"""Top TikTok videos for a product keyword, via the Kalodata Open API.

Resolves a product keyword to the TikTok Shop category it sells in, then
ranks that category's videos by revenue and prints their TikTok URLs.
Run from `data/`::

    python -m scripts.kalodata_top_videos "electric shaver"
    python -m scripts.kalodata_top_videos "electric shaver" --limit 10 --json

Endpoint paths, request fields and response fields all come from
kalodata/kalodata-api.txt. Three calls per run, well inside the ranking
endpoints' 10 requests / 10 seconds.
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

from lib.settings import settings

_TIMEOUT = 30.0

# Undocumented: the ranking endpoints reject page_size below 5 with
# "Invalid Parameter", so smaller requests are padded up and sliced back
# down here rather than being sent as asked.
_MIN_PAGE_SIZE = 5

# Most specific first. A leaf category is the closest match to the product,
# but it can be too narrow to have ranked videos of its own, so its parents
# stay behind it as fallbacks.
_CATEGORY_KEYS = ("ter_cate_id", "sec_cate_id", "pri_cate_id")


def _post(client: httpx.Client, path: str, payload: dict) -> list | dict:
    """POST one Kalodata endpoint and return its ``data`` payload.

    Args:
        client: An open client carrying the ``secret-key`` header.
        path: Endpoint path under the API base, e.g. ``"product/rank"``.
        payload: Request body, merged onto the four common fields.

    Returns:
        The response's ``data`` field: a list for ranking endpoints, an
        object for detail endpoints.

    Raises:
        RuntimeError: If the API reports failure. Kalodata answers HTTP 200
            with ``success: false`` for a rejected key or an unsupported
            filter, so the body has to be checked -- ``raise_for_status``
            alone sees nothing wrong with those.
    """
    body = {
        "region": settings.kalodata.region,
        "language": settings.kalodata.language,
        "currency": settings.kalodata.currency,
        **payload,
    }
    response = client.post(f"{settings.kalodata.base_url}/{path}", json=body)
    response.raise_for_status()
    result = response.json()
    if not result.get("success"):
        raise RuntimeError(f"{path} failed: {result.get('message')} (code {result.get('code')})")
    return result["data"]


def _category_ids(client: httpx.Client, keyword: str, date_range: str) -> list[str]:
    """Resolve a product keyword to the category IDs to search videos in.

    Args:
        client: An open client carrying the ``secret-key`` header.
        keyword: Free-text product search, e.g. ``"electric shaver"``.
        date_range: A Kalodata date range, e.g. ``"last30Day"``.

    Returns:
        Category IDs, most specific first.

    Raises:
        RuntimeError: If no product matches the keyword.
    """
    products = _post(client, "product/rank", {
        "date_range": date_range,
        "sort_field": {"field": "revenue", "type": "DESC"},
        "page_size": _MIN_PAGE_SIZE,
        "page_number": 1,
        "keyword": keyword,
    })
    if not products:
        raise RuntimeError(f"no product matched {keyword!r}")

    detail = _post(client, "product/detail", {
        "date_range": date_range,
        "product_id": products[0]["product_id"],
    })
    return [cid for key in _CATEGORY_KEYS if (cid := detail.get(key))]


def to_row(video: dict) -> dict:
    """Flatten one ``video/rank`` record to the fields worth keeping.

    Kalodata returns no video URL of its own -- TikTok's canonical
    permalink is built from the creator handle and the video id.

    Args:
        video: One element of a ``video/rank`` response's ``data`` array.

    Returns:
        The video's TikTok URL alongside the metrics that say why it ranked.
    """
    handle = video["belonged_creator_handle"]
    return {
        "url": f"https://www.tiktok.com/@{handle}/video/{video['video_id']}",
        "title": video.get("video_title"),
        "creator": handle,
        "revenue": video.get("revenue"),
        "views": video.get("views"),
        "ads_roas": video.get("ads_roas"),
        "ai_video": video.get("ai_video"),
    }


def top_videos(keyword: str, *, date_range: str = "last30Day", limit: int = 10) -> list[dict]:
    """Return the highest-revenue videos in the category a keyword sells in.

    Args:
        keyword: Free-text product search, e.g. ``"electric shaver"``.
        date_range: A Kalodata date range. Ranking endpoints cap the window
            at 30 days, so ``last30Day`` is the widest useful value.
        limit: How many videos to return. The API's page cap is 100.

    Returns:
        Up to ``limit`` rows from :func:`to_row`, highest revenue first.
        Empty only if none of the product's categories has ranked videos.

    Raises:
        RuntimeError: If the API key is unset or the API reports failure.
    """
    if not settings.kalodata.api_key.get_secret_value():
        raise RuntimeError("KALODATA_API_KEY is unset -- add it to data/.env")

    headers = {"secret-key": settings.kalodata.api_key.get_secret_value()}
    with httpx.Client(timeout=_TIMEOUT, headers=headers) as client:
        for category_id in _category_ids(client, keyword, date_range):
            videos = _post(client, "video/rank", {
                "date_range": date_range,
                "sort_field": {"field": "revenue", "type": "DESC"},
                "page_size": max(limit, _MIN_PAGE_SIZE),
                "page_number": 1,
                "category_ids": [category_id],
            })
            if videos:
                return [to_row(v) for v in videos[:limit]]
    return []


def main() -> int:
    """Parse arguments, fetch the ranking, print it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("keyword", help='product to search, e.g. "electric shaver"')
    parser.add_argument("--limit", type=int, default=10, help="how many videos (default 10)")
    parser.add_argument("--date-range", default="last30Day", help="Kalodata date range")
    parser.add_argument("--json", action="store_true", help="print rows as JSON, not as text")
    args = parser.parse_args()

    try:
        rows = top_videos(args.keyword, date_range=args.date_range, limit=args.limit)
    except (RuntimeError, httpx.HTTPError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    if not rows:
        print(f"no ranked videos for {args.keyword!r}")
        return 0
    for i, row in enumerate(rows, 1):
        print(f"{i:2}. {row['url']}")
        print(f"    revenue={row['revenue']} views={row['views']} ai_video={row['ai_video']}")
        print(f"    {row['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
