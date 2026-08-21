"""Top TikTok videos for a product keyword, via the Kalodata Open API.

Resolves a product keyword to the TikTok Shop category it sells in, then
ranks that category's videos by revenue and prints their TikTok URLs.
Run from `data/`::

    python -m scripts.kalodata_top_videos "electric shaver"
    python -m scripts.kalodata_top_videos "electric shaver" --limit 10 --json

Endpoint paths, request fields and response fields all come from
kalodata/kalodata-api.txt. A handful of calls per run -- product/rank,
product/detail, up to a few video/rank tries across three narrowing tiers,
category/detail -- well inside the ranking endpoints' 10 requests / 10
seconds.
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


def _resolve_product(
    client: httpx.Client, keyword: str, date_range: str
) -> tuple[str, str, list[str]]:
    """Resolve a product keyword to its id, name and the category IDs it sells in.

    Args:
        client: An open client carrying the ``secret-key`` header.
        keyword: Free-text product search, e.g. ``"electric shaver"``.
        date_range: A Kalodata date range, e.g. ``"last30Day"``.

    Returns:
        The top-matching product's id, its name, and its category IDs
        (most specific first).

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
    top = products[0]

    detail = _post(client, "product/detail", {
        "date_range": date_range,
        "product_id": top["product_id"],
    })
    category_ids = [cid for key in _CATEGORY_KEYS if (cid := detail.get(key))]
    return top["product_id"], top["product_name"], category_ids


def _category_name(client: httpx.Client, category_id: str, date_range: str) -> str:
    """Look up a category's display name, falling back to its ID.

    Args:
        client: An open client carrying the ``secret-key`` header.
        category_id: A category ID as returned by ``product/detail``.
        date_range: A Kalodata date range. ``category/detail`` only accepts
            the named ranges (not a natural ``yyyy-MM-dd~yyyy-MM-dd`` span),
            so an unsupported range falls back to the ID rather than raising.

    Returns:
        ``category_name``, or ``category_id`` if the lookup fails.
    """
    try:
        detail = _post(client, "category/detail", {
            "date_range": date_range,
            "category_id": category_id,
        })
    except RuntimeError:
        return category_id
    return detail.get("category_name") or category_id


def to_row(video: dict, *, product_name: str, category_name: str) -> dict:
    """Flatten one ``video/rank`` record to the fields worth keeping.

    Kalodata returns no video URL of its own -- TikTok's canonical
    permalink is built from the creator handle and the video id.

    Args:
        video: One element of a ``video/rank`` response's ``data`` array.
        product_name: The keyword's top-matching product name (same for
            every row in one ``top_videos`` call).
        category_name: The video's ranked category name (same for every
            row in one ``top_videos`` call).

    Returns:
        The video's TikTok URL alongside the metrics that say why it ranked.
    """
    handle = video["belonged_creator_handle"]
    return {
        "video_id": video["video_id"],
        "url": f"https://www.tiktok.com/@{handle}/video/{video['video_id']}",
        "title": video.get("video_title"),
        "creator": handle,
        "revenue": video.get("revenue"),
        "views": video.get("views"),
        "ads_roas": video.get("ads_roas"),
        "ai_video": video.get("ai_video"),
        "product_name": product_name,
        "category_name": category_name,
    }


def top_videos(keyword: str, *, date_range: str = "last30Day", limit: int = 10) -> list[dict]:
    """Return the highest-revenue videos that actually feature a keyword's product.

    Tries three tiers, each broader than the last -- ``video/rank`` has no
    "search within this category" mode of its own, so the narrowing has to
    be layered as separate calls:

    1. ``product_id`` -- videos that mount the exact top-matching product.
       The precise answer: these videos are demonstrably about it.
    2. ``category_ids`` + ``keyword`` -- the resolved category, filtered by
       the same keyword against video titles. Broader than (1) but still
       text-relevant when no video mounts that specific product listing.
    3. ``category_ids`` alone -- top-revenue videos anywhere in the
       category. Only reached when neither of the above found anything;
       these can be about a different product in the same category
       (Kalodata has no finer filter to fall back to).

    Args:
        keyword: Free-text product search, e.g. ``"electric shaver"``.
        date_range: A Kalodata date range. Ranking endpoints cap the window
            at 30 days, so ``last30Day`` is the widest useful value.
        limit: How many videos to return. The API's page cap is 100.

    Returns:
        Up to ``limit`` rows from :func:`to_row`, highest revenue first,
        from the narrowest tier that found anything. Empty only if none of
        the three tiers has ranked videos.

    Raises:
        RuntimeError: If the API key is unset or the API reports failure.
    """
    if not settings.kalodata.api_key.get_secret_value():
        raise RuntimeError("KALODATA_API_KEY is unset -- add it to data/.env")

    def _rank(client: httpx.Client, **filters: object) -> list[dict]:
        return _post(client, "video/rank", {
            "date_range": date_range,
            "sort_field": {"field": "revenue", "type": "DESC"},
            "page_size": max(limit, _MIN_PAGE_SIZE),
            "page_number": 1,
            **filters,
        })

    headers = {"secret-key": settings.kalodata.api_key.get_secret_value()}
    with httpx.Client(timeout=_TIMEOUT, headers=headers) as client:
        product_id, product_name, category_ids = _resolve_product(client, keyword, date_range)
        primary_category_id = category_ids[0] if category_ids else None

        videos = _rank(client, product_id=product_id)
        if not videos and primary_category_id:
            for category_id in category_ids:
                videos = _rank(client, category_ids=[category_id], keyword=keyword)
                if videos:
                    break
        if not videos:
            for category_id in category_ids:
                videos = _rank(client, category_ids=[category_id])
                if videos:
                    break

        if not videos:
            return []
        category_name = _category_name(client, primary_category_id, date_range) \
            if primary_category_id else ""
        return [
            to_row(v, product_name=product_name, category_name=category_name)
            for v in videos[:limit]
        ]


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
