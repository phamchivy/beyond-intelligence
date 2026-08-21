"""Turn downloaded TikTok videos into scene-by-scene storyboards.

Reads video blobs already fetched by ``kalodata_download_videos.py``, asks
Gemini for a storyboard per video, and writes one Silver row per scene. Run
from `data/`::

    python -m scripts.kalodata_analyze_videos
    python -m scripts.kalodata_analyze_videos --limit 3 --markdown
    python -m scripts.kalodata_analyze_videos --markdown-out refs.md

A video already analyzed at the current ``GEMINI_PROMPT_VERSION`` is
skipped -- re-running makes zero model calls until the prompt or model
changes (architecture doc §6.6's caching rule).

The storyboards describe someone else's videos. They are a reference for
what converts in a category -- using them to inform your own script is
ordinary competitive research; reproducing a specific video shot-for-shot
is not.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pyarrow as pa

from contracts.video_storyboard import VideoStoryboardSchema
from lib.contracts import split_on_contract
from lib.delta import read_delta, s3_filesystem, table_version, write_delta
from lib.gemini import analyze_video
from lib.logging import get_logger, log_event
from lib.settings import settings

logger = get_logger(__name__)


@dataclass
class AnalyzeResult:
    """One video's outcome: analyzed with a storyboard, or failed with none."""

    video_id: str
    bronze_row: dict
    scenes: list[dict]  # Silver rows for this video; empty unless analyzed
    storyboard: dict | None  # hook/cta/summary/scenes, for markdown; None on failure
    analyzed: bool


def _all_bronze_rows() -> list[dict]:
    """Every row in Bronze ``tiktok_video``, most recently fetched first."""
    if table_version("bronze", "tiktok_video") is None:
        return []
    df = pl.from_arrow(read_delta("bronze", "tiktok_video"))
    return df.sort("fetched_at", descending=True).to_dicts()


def _already_analyzed_ids(prompt_version: str) -> set[str]:
    """Video IDs that already have a Silver storyboard at ``prompt_version``."""
    if table_version("silver", "video_storyboard") is None:
        return set()
    df = pl.from_arrow(read_delta("silver", "video_storyboard"))
    matching = df.filter(pl.col("prompt_version") == prompt_version)
    return set(matching.get_column("video_id").unique().to_list())


def _analyze_one(fs, bronze_row: dict, prompt_version: str) -> AnalyzeResult:
    """Download one video's blob and turn it into a storyboard.

    Args:
        fs: An open S3 filesystem handle.
        bronze_row: One row from ``bronze/tiktok_video`` -- needs ``s3_key``.
        prompt_version: Recorded on every scene row as the idempotency key.

    Returns:
        The outcome. A download or model failure is logged and returned
        as ``analyzed=False`` rather than raised -- one dead video must
        not lose the rest of the run.
    """
    video_id = bronze_row["video_id"]
    with tempfile.TemporaryDirectory() as tmp:
        local_path = Path(tmp) / f"{video_id}.mp4"
        try:
            fs.get(bronze_row["s3_key"], str(local_path))
            storyboard = analyze_video(local_path, prompt_version=prompt_version)
        except (RuntimeError, OSError) as exc:
            log_event(logger, "warning", "video_analyze_failed", video_id=video_id, error=str(exc))
            return AnalyzeResult(video_id, bronze_row, scenes=[], storyboard=None, analyzed=False)

    scenes = [
        {
            "video_id": video_id,
            "prompt_version": prompt_version,
            "scene_no": scene["scene_no"],
            "t_start": float(scene["t_start"]),
            "t_end": float(scene["t_end"]),
            "shot_type": scene["shot_type"],
            "visual": scene["visual"],
            "on_screen_text": scene["on_screen_text"],
            "voiceover": scene["voiceover"],
            "hook": storyboard["hook"],
            "cta": storyboard["cta"],
            "summary": storyboard["summary"],
        }
        for scene in storyboard["scenes"]
    ]
    log_event(logger, "info", "video_analyzed", video_id=video_id, scene_count=len(scenes))
    return AnalyzeResult(video_id, bronze_row, scenes=scenes, storyboard=storyboard, analyzed=True)


def analyze_top_videos(*, limit: int | None = None) -> tuple[list[AnalyzeResult], int]:
    """Analyze every Bronze video not yet analyzed at the current prompt version.

    Args:
        limit: Cap on how many *new* videos to analyze this run.
            Already-analyzed videos are never counted against it.

    Returns:
        A tuple of (results for every video attempted this run, count of
        candidate videos that were already analyzed and skipped).
    """
    prompt_version = settings.gemini.prompt_version
    bronze_rows = _all_bronze_rows()
    done_ids = _already_analyzed_ids(prompt_version)

    skipped_count = sum(1 for row in bronze_rows if row["video_id"] in done_ids)
    todo = [row for row in bronze_rows if row["video_id"] not in done_ids]
    if limit is not None:
        todo = todo[:limit]

    if not todo:
        return [], skipped_count

    fs = s3_filesystem()
    results = [_analyze_one(fs, row, prompt_version) for row in todo]
    return results, skipped_count


def _write_silver(results: list[AnalyzeResult]) -> int | None:
    """Validate and append every analyzed video's scene rows to Silver.

    Args:
        results: Output of :func:`analyze_top_videos`.

    Returns:
        The Delta commit version, or ``None`` if nothing new was analyzed.
    """
    all_scenes = [scene for r in results for scene in r.scenes]
    if not all_scenes:
        return None

    table: pa.Table = pl.DataFrame(all_scenes).to_arrow()
    good, bad = split_on_contract(table, VideoStoryboardSchema)
    if bad.num_rows:
        write_delta("quarantine", "video_storyboard", bad, mode="append")
        log_event(logger, "warning", "video_storyboard_quarantined", row_count=bad.num_rows)
    if not good.num_rows:
        return None
    return write_delta("silver", "video_storyboard", good, mode="append")


def render_markdown(results: list[AnalyzeResult]) -> str:
    """Render every successfully analyzed video as a prompt-ready reference block.

    Args:
        results: Output of :func:`analyze_top_videos`.

    Returns:
        Markdown, one section per analyzed video, separated by ``---``.
        Empty string if nothing was analyzed this run.
    """
    blocks = []
    for r in results:
        if not r.analyzed:
            continue
        b, sb = r.bronze_row, r.storyboard
        category = b.get("category_name") or "Unknown"
        revenue = b.get("revenue") or 0
        views = b.get("views") or 0
        kind = "AI-generated" if b.get("ai_video") else "organic"

        rows = "\n".join(
            f"| {s['scene_no']} | {s['t_start']:.0f}s | {s['shot_type']} | {s['visual']} | "
            f"{s['on_screen_text']} | {s['voiceover']} |"
            for s in sb["scenes"]
        )
        blocks.append(
            f"## Trending reference — {category}\n"
            f"Revenue ${revenue:,.0f} · {views:,} views · {kind}\n\n"
            f"HOOK: {sb['hook']}\n\n"
            "| # | time | shot | visual | on-screen text | voiceover |\n"
            "|---|------|------|--------|----------------|-----------|\n"
            f"{rows}\n\n"
            f"CTA: {sb['cta']}"
        )
    return "\n\n---\n\n".join(blocks)


def main() -> int:
    """Parse arguments, analyze, write Silver, optionally render markdown."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=None, help="max new videos to analyze")
    parser.add_argument("--markdown", action="store_true", help="print the prompt-ready reference")
    parser.add_argument("--markdown-out", help="write the prompt-ready reference to this file")
    args = parser.parse_args()

    try:
        results, skipped = analyze_top_videos(limit=args.limit)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    analyzed = sum(r.analyzed for r in results)
    failed = len(results) - analyzed
    version = _write_silver(results)

    print(f"{analyzed} analyzed, {skipped} skipped, {failed} failed")
    if version is not None:
        print(f"silver/video_storyboard -> version {version}")

    if args.markdown or args.markdown_out:
        md = render_markdown(results)
        if args.markdown_out:
            Path(args.markdown_out).write_text(md)
            print(f"markdown written to {args.markdown_out}")
        else:
            print()
            print(md)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
