"""Index Silver video storyboards into the retrieval index.

Reads ``silver/video_storyboard``, joins the Kalodata metrics from
``bronze/tiktok_video``, and upserts one searchable chunk per video into
``index.chunk`` / ``index.embedding``. Run from `data/`::

    python -m scripts.index_storyboards

One chunk per *video*, not per scene: the trending endpoint returns videos,
so the video is the retrieval unit and nothing has to be de-duplicated
afterwards.

``upsert_chunks`` is already ON CONFLICT DO UPDATE, so re-running refreshes
rather than duplicating -- no extra idempotency machinery here.
"""

from __future__ import annotations

import sys

import polars as pl

from lib import db
from lib.delta import read_delta, table_version
from lib.embedding import MODEL_ID, embed
from lib.logging import get_logger, log_event
from lib.settings import settings

logger = get_logger(__name__)

SOURCE_TYPE = "video_storyboard"


def _searchable_text(video: dict, scenes: list[dict]) -> str:
    """Build the text a query is matched against for one video.

    Title, product and category lead: a query is a product or category
    name far more often than it is a line of dialogue, and the dense leg
    weights early tokens.

    Args:
        video: The video's Bronze row (title, product_name, category_name).
        scenes: That video's Silver scene rows, in scene order.

    Returns:
        One flat string covering the video's identity and its whole script.
    """
    head = [
        video.get("title") or "",
        video.get("product_name") or "",
        video.get("category_name") or "",
        f"HOOK: {scenes[0]['hook']}",
        f"SUMMARY: {scenes[0]['summary']}",
    ]
    body = [
        f"{s['shot_type']}: {s['visual']} {s['on_screen_text']} {s['voiceover']}".strip()
        for s in scenes
    ]
    return " | ".join(part for part in [*head, *body, f"CTA: {scenes[0]['cta']}"] if part.strip())


def _storyboard(scenes: list[dict]) -> dict:
    """Reassemble the nested storyboard from its flat Silver scene rows."""
    return {
        "hook": scenes[0]["hook"],
        "hook_style": scenes[0].get("hook_style"),
        "cta": scenes[0]["cta"],
        "summary": scenes[0]["summary"],
        "scenes": [
            {
                "scene_no": s["scene_no"],
                "t_start": s["t_start"],
                "t_end": s["t_end"],
                "shot_type": s["shot_type"],
                "visual": s["visual"],
                "on_screen_text": s["on_screen_text"],
                "voiceover": s["voiceover"],
            }
            for s in scenes
        ],
    }


def build_chunks() -> list[dict]:
    """Build one index chunk per video that has a storyboard.

    Returns:
        Chunk dicts ready for :func:`lib.db.upsert_chunks`. ``metadata``
        carries the storyboard itself plus the ranking signals, so the
        endpoint needs no S3 or Delta read per request. Empty if either
        Silver or Bronze has nothing yet.
    """
    if table_version("silver", "video_storyboard") is None:
        return []
    if table_version("bronze", "tiktok_video") is None:
        return []

    # Silver is append-only and holds every prompt_version ever written;
    # without this filter, a video re-analyzed under a newer prompt would
    # have both versions' scenes interleave into one chunk.
    scenes_df = (
        pl.from_arrow(read_delta("silver", "video_storyboard"))
        .filter(pl.col("prompt_version") == settings.gemini.prompt_version)
        .sort("scene_no")
    )
    bronze_by_id = {
        row["video_id"]: row
        for row in pl.from_arrow(read_delta("bronze", "tiktok_video")).to_dicts()
    }

    chunks = []
    for (video_id,), group in scenes_df.group_by("video_id", maintain_order=True):
        video = bronze_by_id.get(video_id)
        if video is None:
            # A storyboard whose Bronze row is missing has no metrics to
            # rank by; indexing it would put an unrankable video in the
            # candidate set.
            log_event(logger, "warning", "storyboard_without_bronze_row", video_id=video_id)
            continue

        scenes = group.to_dicts()
        chunks.append({
            "chunk_id": f"VID-{video_id}",
            "document_id": video_id,
            "source_type": SOURCE_TYPE,
            "chunk_index": 0,
            "content": _searchable_text(video, scenes),
            "metadata": {
                "video_id": video_id,
                "title": video.get("title"),
                "url": video.get("url"),
                "category_name": video.get("category_name"),
                "product_name": video.get("product_name"),
                "matched_keyword": video.get("keyword"),
                "revenue": video.get("revenue"),
                "views": video.get("views"),
                "ai_video": video.get("ai_video"),
                "ad": video.get("ad"),
                "digg_count": video.get("digg_count"),
                "share_count": video.get("share_count"),
                "comment_count": video.get("comment_count"),
                "creator_debut": video.get("creator_debut"),
                "duration_s": video.get("duration_s"),
                "fetched_at": video.get("fetched_at"),
                "storyboard": _storyboard(scenes),
            },
        })
    return chunks


def main() -> int:
    """Build the chunks, embed them, and upsert into the retrieval index."""
    chunks = build_chunks()
    if not chunks:
        print("nothing to index -- no storyboards in silver/video_storyboard")
        return 0

    vectors = embed([c["content"] for c in chunks])
    db.upsert_chunks(chunks, vectors, embedder_model_id=MODEL_ID)
    db.dump_index_to_delta()
    log_event(logger, "info", "storyboards_indexed", chunk_count=len(chunks))

    print(f"{len(chunks)} storyboards indexed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
