"""Download Kalodata's top-ranked TikTok videos into Landing.

Resolves a product keyword to its top videos (``kalodata_top_videos.py``),
downloads each one once, and records the fetch alongside the Kalodata
metrics that made it interesting. Run from `data/`::

    python -m scripts.kalodata_download_videos "electric shaver"
    python -m scripts.kalodata_download_videos "electric shaver" --limit 10

Blobs land at ``landing/tiktok/{video_id}.mp4``; one row per video is
appended to the Bronze table ``tiktok_video``. A video already present in
Landing is skipped, not re-downloaded -- a TikTok video's bytes never
change, so ``video_id`` is a stable idempotency key.

This fetches TikTok videos into private storage for internal analysis.
That is ordinary research use, but it is not something TikTok's terms
invite -- keep the blobs internal, never re-publish them.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pyarrow as pa
import yt_dlp

from lib.delta import sha256_file, write_delta
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


@dataclass
class FetchResult:
    """One video's outcome: either it landed, was already there, or failed."""

    video_id: str
    row: dict | None  # None means skipped-or-failed; nothing to add to Bronze
    downloaded: bool
    skipped: bool


def _landing_fs():
    """Build the S3 filesystem handle, same construction as defs/ingest.py.

    Imported lazily -- s3fs pulls in aiobotocore, whose pinned botocore
    range can drift from the one another dependency installed in this
    venv (pre-existing, unrelated to this script -- defs/ingest.py hits
    the same import failure). Importing it only when a real upload is
    about to happen keeps that fragility from blocking module import in
    unit tests, which never call this function.

    Returns:
        An ``s3fs.S3FileSystem`` pointed at the configured storage endpoint.
    """
    import s3fs

    client_kwargs = {"region_name": settings.storage.region}
    if settings.storage.is_local:
        client_kwargs["endpoint_url"] = settings.storage.endpoint_url

    return s3fs.S3FileSystem(
        key=settings.storage.access_key,
        secret=settings.storage.secret_key,
        client_kwargs=client_kwargs,
        config_kwargs={"s3": {"addressing_style": settings.storage.addressing_style}},
    )


def _landing_key(video_id: str) -> str:
    """Return the Landing object key for one video, without the ``s3://`` scheme."""
    root = settings.storage.landing_url.replace("s3://", "")
    return f"{root}/tiktok/{video_id}.mp4"


def _download_one(fs, row: dict, keyword: str) -> FetchResult:
    """Fetch one ranked video into Landing, unless it is already there.

    Args:
        fs: An open ``s3fs.S3FileSystem`` handle (untyped here -- s3fs is
            imported lazily, see :func:`_landing_fs`).
        row: One row from :func:`scripts.kalodata_top_videos.top_videos`.
        keyword: The product keyword this run was searched under.

    Returns:
        The outcome -- downloaded, skipped as already-present, or failed.
    """
    video_id = row["video_id"]
    key = _landing_key(video_id)

    if fs.exists(key):
        log_event(logger, "info", "video_skipped_existing", video_id=video_id)
        return FetchResult(video_id, None, downloaded=False, skipped=True)

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
    fs = _landing_fs()
    return [_download_one(fs, row, keyword) for row in rows]


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
