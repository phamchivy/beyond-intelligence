"""Download Kalodata's top-ranked TikTok videos into Landing.

Resolves a product keyword to its top videos (``kalodata_top_videos.py``),
downloads each one once, and records the fetch alongside the Kalodata
metrics that made it interesting. Run from `data/`::

    python -m scripts.kalodata_download_videos "electric shaver"
    python -m scripts.kalodata_download_videos "electric shaver" --limit 10

Blobs land at
``trending_tiktok_videos/landing/{category}/{product}/{date}/{title}_{video_id}_{timestamp}.mp4``;
one row per video is appended to the Bronze table ``tiktok_video``. A
video already fetched for that category/product/day is skipped, not
re-downloaded -- matched by ``video_id`` inside the filename, since the
timestamp changes on every run.

This fetches TikTok videos into private storage for internal analysis.
That is ordinary research use, but it is not something TikTok's terms
invite -- keep the blobs internal, never re-publish them.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pyarrow as pa
import yt_dlp

from lib.delta import s3_filesystem, sha256_file, write_delta
from lib.logging import get_logger, log_event
from lib.settings import settings
from scripts.kalodata_top_videos import top_videos

logger = get_logger(__name__)

# Trust boundary: these bytes come from an attacker-influenceable remote
# source (whatever TikTok video ranked highest today). An uncapped fetch
# is how the bucket fills.
_MAX_FILESIZE_BYTES = 200 * 1024 * 1024

# A single progressive file, deliberately. yt-dlp's default selector picks
# separate video/audio streams and shells out to ffmpeg to merge them, and
# this project carries no ffmpeg (data-architecture.md #6: "no media: no
# ffmpeg, no google-genai").
_FORMAT = "best[ext=mp4]/best"

_ROOT = "trending_tiktok_videos/landing"
_SLUG_RE = re.compile(r"[^\w\-]+", re.UNICODE)


def _slug(text: str, *, max_len: int = 60) -> str:
    """Turn free text into a safe, readable S3 key segment.

    Args:
        text: A category name, product name or video title -- any of
            which can carry slashes, hashtags, emoji or punctuation that
            would otherwise corrupt the key's path structure.
        max_len: Truncation length, keeping keys well under S3's 1024-byte
            cap even for a long video title.

    Returns:
        Anything but word characters and hyphens collapsed to a single
        underscore, or ``"unknown"`` if that leaves nothing.
    """
    slug = _SLUG_RE.sub("_", text or "").strip("_")
    return slug[:max_len].strip("_") or "unknown"


@dataclass
class FetchResult:
    """One video's outcome: either it landed, was already there, or failed."""

    video_id: str
    row: dict | None  # None means skipped-or-failed; nothing to add to Bronze
    downloaded: bool
    skipped: bool


def _day_prefix(category_name: str, product_name: str, date_str: str) -> str:
    """Return the day-partitioned Landing prefix for one category/product.

    Args:
        category_name: The video's ranked category name.
        product_name: The keyword's top-matching product name.
        date_str: The run's date, ``YYYY-MM-DD``.

    Returns:
        A key prefix, without the ``s3://`` scheme, ending in ``/``.
    """
    root = settings.storage.url.replace("s3://", "")
    return f"{root}/{_ROOT}/{_slug(category_name)}/{_slug(product_name)}/{date_str}/"


def _landing_key(prefix: str, title: str, video_id: str, timestamp: str) -> str:
    """Build one video's object key under an already-resolved day prefix."""
    return f"{prefix}{_slug(title)}_{video_id}_{timestamp}.mp4"


def _existing_key(fs, prefix: str, video_id: str) -> str | None:
    """Return today's already-fetched key for this video, if any.

    The timestamp in every key changes on every run, so an exact-key
    ``fs.exists`` check can never match a prior run -- instead this globs
    the day's prefix for a filename carrying this ``video_id``, which is
    the one part of the name that stays stable for the same video on the
    same day.

    Args:
        fs: An open ``s3fs.S3FileSystem`` handle.
        prefix: A day prefix from :func:`_day_prefix`.
        video_id: The TikTok video ID to look for.

    Returns:
        The matching key, or ``None`` if this video has not been fetched
        into this prefix yet today.
    """
    matches = fs.glob(f"{prefix}*_{video_id}_*.mp4")
    return matches[0] if matches else None


def _download_one(fs, row: dict, keyword: str, prefix: str, timestamp: str) -> FetchResult:
    """Fetch one ranked video into Landing, unless it is already there today.

    Args:
        fs: An open ``s3fs.S3FileSystem`` handle (untyped here -- s3fs is
            see :func:`lib.delta.s3_filesystem`).
        row: One row from :func:`scripts.kalodata_top_videos.top_videos`.
        keyword: The product keyword this run was searched under.
        prefix: This run's day prefix, from :func:`_day_prefix`.
        timestamp: This run's timestamp, shared by every video fetched in
            the same run.

    Returns:
        The outcome -- downloaded, skipped as already-present, or failed.
    """
    video_id = row["video_id"]

    if _existing_key(fs, prefix, video_id):
        log_event(logger, "info", "video_skipped_existing", video_id=video_id)
        return FetchResult(video_id, None, downloaded=False, skipped=True)

    key = _landing_key(prefix, row.get("title") or video_id, video_id, timestamp)

    with tempfile.TemporaryDirectory() as tmp:
        local_path = Path(tmp) / f"{video_id}.mp4"
        opts = {
            "format": _FORMAT,
            "outtmpl": str(local_path),
            "max_filesize": _MAX_FILESIZE_BYTES,
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(row["url"], download=True)
        except yt_dlp.utils.DownloadError as exc:
            log_event(logger, "warning", "video_download_failed", video_id=video_id, error=str(exc))
            return FetchResult(video_id, None, downloaded=False, skipped=False)

        digest = sha256_file(local_path)
        fs.put(str(local_path), key)

    log_event(logger, "info", "video_downloaded", video_id=video_id, sha256=digest)
    return FetchResult(
        video_id,
        {
            "video_id": video_id,
            "url": row["url"],
            "s3_key": key,
            "sha256": digest,
            "size_bytes": local_path.stat().st_size if local_path.exists() else None,
            "duration_s": info.get("duration") if info else None,
            "keyword": keyword,
            "fetched_at": int(time.time()),
            "title": row.get("title"),
            "creator": row.get("creator"),
            "revenue": row.get("revenue"),
            "views": row.get("views"),
            "ads_roas": row.get("ads_roas"),
            "ai_video": row.get("ai_video"),
            "ad": row.get("ad"),
            "digg_count": row.get("digg_count"),
            "share_count": row.get("share_count"),
            "comment_count": row.get("comment_count"),
            "creator_debut": row.get("creator_debut"),
            "product_name": row.get("product_name"),
            "category_name": row.get("category_name"),
        },
        downloaded=True,
        skipped=False,
    )


def download_top_videos(
    keyword: str, *, date_range: str = "last30Day", limit: int = 10
) -> list[FetchResult]:
    """Rank, then download, the top videos for a product keyword.

    Args:
        keyword: Free-text product search, e.g. ``"electric shaver"``.
        date_range: A Kalodata date range, forwarded to ``top_videos``.
        limit: How many videos to fetch.

    Returns:
        One :class:`FetchResult` per ranked video, in ranked order. A
        failed download does not stop the rest -- one dead video must not
        lose the other nine.
    """
    rows = top_videos(keyword, date_range=date_range, limit=limit)
    if not rows:
        return []

    # One category/product/day prefix and one timestamp for the whole run --
    # every row shares the same resolved category and product (top_videos
    # ranks within a single category per call), and a per-run timestamp
    # keeps a batch of videos fetched together grouped by name.
    now = datetime.now(UTC)
    date_str = now.strftime("%Y-%m-%d")
    prefix = _day_prefix(rows[0]["category_name"], rows[0]["product_name"], date_str)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")

    fs = s3_filesystem()
    return [_download_one(fs, row, keyword, prefix, timestamp) for row in rows]


def _write_bronze(results: list[FetchResult]) -> int | None:
    """Append the fetched rows to the Bronze ``tiktok_video`` table.

    Args:
        results: Output of :func:`download_top_videos`.

    Returns:
        The Delta commit version, or ``None`` if nothing new was fetched.
    """
    new_rows = [r.row for r in results if r.row is not None]
    if not new_rows:
        return None
    table: pa.Table = pl.DataFrame(new_rows).to_arrow()
    return write_delta("bronze", "tiktok_video", table, mode="append")


def main() -> int:
    """Parse arguments, download, report, write Bronze."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("keyword", help='product to search, e.g. "electric shaver"')
    parser.add_argument("--limit", type=int, default=10, help="how many videos (default 10)")
    parser.add_argument("--date-range", default="last30Day", help="Kalodata date range")
    args = parser.parse_args()

    try:
        results = download_top_videos(args.keyword, date_range=args.date_range, limit=args.limit)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    downloaded = sum(r.downloaded for r in results)
    skipped = sum(r.skipped for r in results)
    failed = len(results) - downloaded - skipped
    version = _write_bronze(results)

    print(f"{downloaded} downloaded, {skipped} skipped, {failed} failed")
    if version is not None:
        print(f"bronze/tiktok_video -> version {version}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
