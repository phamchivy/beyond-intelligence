"""Daily trending pipeline: discover -> fetch -> analyze -> index.

Auto-discovers today's top-revenue categories and products via Kalodata
(no manual keyword), then runs the existing per-keyword chain for each:
download new videos into Bronze, analyze every new Bronze row with Gemini,
and re-index Silver into the retrieval index. Meant to run once daily from
a cron-triggered container (see Dockerfile.pipeline). Run from `data/`::

    python -m scripts.kalodata_daily_pipeline

Safe to run twice in the same day -- every step is already idempotent
(Bronze/Silver dedup by video_id, index upsert by chunk_id).
"""

from __future__ import annotations

import sys

from lib.logging import get_logger, log_event
from scripts import index_storyboards
from scripts.kalodata_analyze_videos import _write_silver, analyze_top_videos
from scripts.kalodata_download_videos import _write_bronze, download_top_videos
from scripts.kalodata_top_videos import discover_keywords

logger = get_logger(__name__)


def main() -> int:
    """Discover today's trending keywords, then fetch, analyze and index them."""
    keywords = discover_keywords()
    log_event(logger, "info", "daily_pipeline_keywords_discovered",
              keyword_count=len(keywords), keywords=keywords)

    fetched = 0
    for keyword in keywords:
        try:
            results = download_top_videos(keyword)
        except RuntimeError as exc:
            log_event(logger, "warning", "daily_pipeline_keyword_failed",
                      keyword=keyword, error=str(exc))
            continue
        _write_bronze(results)
        fetched += sum(r.downloaded for r in results)

    analyzed, skipped = analyze_top_videos()
    _write_silver(analyzed)
    index_storyboards.main()

    analyzed_count = sum(r.analyzed for r in analyzed)
    log_event(logger, "info", "daily_pipeline_complete", keywords_tried=len(keywords),
              videos_fetched=fetched, videos_analyzed=analyzed_count,
              videos_already_analyzed=skipped)
    print(
        f"{len(keywords)} keywords, {fetched} videos fetched, "
        f"{analyzed_count} newly analyzed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
