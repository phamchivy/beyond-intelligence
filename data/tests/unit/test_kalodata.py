"""Unit tests for scripts/kalodata_top_videos.py -- httpx is stubbed, no network."""

from __future__ import annotations

import json

import httpx
import pytest

from lib.settings import settings
from scripts import kalodata_top_videos as k


def _responder(routes: dict[str, dict]) -> httpx.MockTransport:
    """Answer each endpoint path with its canned body from ``routes``."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/openapi/v1/tiktok/", 1)[-1]
        return httpx.Response(200, json=routes[path])

    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the settings singleton a key so top_videos() gets past its guard."""
    monkeypatch.setattr(settings.kalodata.api_key, "get_secret_value", lambda: "test-key")


@pytest.fixture
def stub_client(monkeypatch: pytest.MonkeyPatch):
    """Return a factory that pins httpx.Client to the given canned routes."""
    def install(routes: dict[str, dict]) -> None:
        transport = _responder(routes)
        real_client = httpx.Client
        monkeypatch.setattr(
            k.httpx, "Client",
            lambda **kwargs: real_client(**{**kwargs, "transport": transport}),
        )

    return install


def test_to_row_builds_the_tiktok_permalink():
    row = k.to_row(
        {
            "video_id": "7404191282148511007",
            "belonged_creator_handle": "jenna_seas",
            "video_title": "the shaver",
            "revenue": 14.99,
            "views": 1519,
            "ai_video": 0,
        },
        product_name="Electric Shaver",
        category_name="Beauty & Personal Care",
    )
    assert row["url"] == "https://www.tiktok.com/@jenna_seas/video/7404191282148511007"
    assert row["creator"] == "jenna_seas"
    assert row["revenue"] == 14.99
    assert row["product_name"] == "Electric Shaver"
    assert row["category_name"] == "Beauty & Personal Care"


def test_to_row_passes_through_ad_flag_engagement_counts_and_creator_debut():
    row = k.to_row(
        {
            "video_id": "7404191282148511007",
            "belonged_creator_handle": "jenna_seas",
            "video_title": "the shaver",
            "revenue": 14.99,
            "views": 1519,
            "ai_video": 0,
            "ad": 1,
            "digg_count": 15000,
            "share_count": 2500,
            "comment_count": 800,
            "creator_debut": "2024-01-15",
        },
        product_name="Electric Shaver",
        category_name="Beauty & Personal Care",
    )
    assert row["ad"] == 1
    assert row["digg_count"] == 15000
    assert row["share_count"] == 2500
    assert row["comment_count"] == 800
    assert row["creator_debut"] == "2024-01-15"


def _install_transport(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    """Point k.httpx.Client at a body-aware MockTransport for one test."""
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        k.httpx, "Client", lambda **kwargs: real_client(**{**kwargs, "transport": transport})
    )


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content)


def test_top_videos_prefers_the_product_id_tier_when_it_has_videos(stub_client):
    """product_id videos -- ones that actually mount the matched product -- win outright."""
    stub_client({
        "product/rank": {"success": True, "data": [
            {"product_id": "p1", "product_name": "Electric Shaver"},
        ]},
        "product/detail": {"success": True, "data": {"ter_cate_id": "601450"}},
        "video/rank": {"success": True, "data": [
            {"video_id": "v1", "belonged_creator_handle": "alice", "revenue": 100.0},
        ]},
        "category/detail": {"success": True, "data": {"category_name": "Beauty"}},
    })
    rows = k.top_videos("electric shaver")
    assert [r["url"] for r in rows] == ["https://www.tiktok.com/@alice/video/v1"]
    assert rows[0]["product_name"] == "Electric Shaver"
    assert rows[0]["category_name"] == "Beauty"


def test_falls_back_to_category_plus_keyword_when_no_video_mounts_the_product(
    monkeypatch: pytest.MonkeyPatch,
):
    """No video for the exact product must not give up -- try category + keyword text next."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/openapi/v1/tiktok/", 1)[-1]
        if path == "product/rank":
            return httpx.Response(200, json={
                "success": True, "data": [{"product_id": "p1", "product_name": "Widget"}],
            })
        if path == "product/detail":
            return httpx.Response(200, json={"success": True, "data": {"ter_cate_id": "cat1"}})
        if path == "category/detail":
            return httpx.Response(200, json={"success": True, "data": {"category_name": "Cat"}})
        body = _body(request)
        if "product_id" in body:
            return httpx.Response(200, json={"success": True, "data": []})
        assert body.get("keyword") == "widget"
        return httpx.Response(200, json={
            "success": True,
            "data": [{"video_id": "v2", "belonged_creator_handle": "carl", "revenue": 7.0}],
        })

    _install_transport(monkeypatch, handler)
    rows = k.top_videos("widget")
    assert [r["url"] for r in rows] == ["https://www.tiktok.com/@carl/video/v2"]


def test_falls_back_to_category_alone_when_keyword_also_finds_nothing(
    monkeypatch: pytest.MonkeyPatch,
):
    """Last resort: top-revenue videos anywhere in the category, no product or text match."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/openapi/v1/tiktok/", 1)[-1]
        if path == "product/rank":
            return httpx.Response(200, json={
                "success": True, "data": [{"product_id": "p1", "product_name": "Widget"}],
            })
        if path == "product/detail":
            return httpx.Response(200, json={"success": True, "data": {"ter_cate_id": "cat1"}})
        if path == "category/detail":
            return httpx.Response(200, json={"success": True, "data": {"category_name": "Cat"}})
        body = _body(request)
        if "product_id" in body or "keyword" in body:
            return httpx.Response(200, json={"success": True, "data": []})
        return httpx.Response(200, json={
            "success": True,
            "data": [{"video_id": "v3", "belonged_creator_handle": "dee", "revenue": 3.0}],
        })

    _install_transport(monkeypatch, handler)
    rows = k.top_videos("widget")
    assert [r["url"] for r in rows] == ["https://www.tiktok.com/@dee/video/v3"]


def test_falls_back_to_a_broader_category_within_the_keyword_tier_when_the_leaf_is_empty(
    monkeypatch: pytest.MonkeyPatch,
):
    """A leaf category with no keyword-matched videos must not end the search early."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/openapi/v1/tiktok/", 1)[-1]
        if path == "product/rank":
            return httpx.Response(200, json={
                "success": True, "data": [{"product_id": "p1", "product_name": "Widget"}],
            })
        if path == "product/detail":
            return httpx.Response(200, json={
                "success": True,
                "data": {"ter_cate_id": "leaf", "sec_cate_id": "mid", "pri_cate_id": "top"},
            })
        if path == "category/detail":
            return httpx.Response(200, json={"success": True, "data": {"category_name": "Mid"}})
        body = _body(request)
        if "product_id" in body:
            return httpx.Response(200, json={"success": True, "data": []})
        which = "leaf" if body.get("category_ids") == ["leaf"] else "mid"
        seen.append(which)
        data = [] if which == "leaf" else [
            {"video_id": "v9", "belonged_creator_handle": "bob", "revenue": 5.0}
        ]
        return httpx.Response(200, json={"success": True, "data": data})

    _install_transport(monkeypatch, handler)
    rows = k.top_videos("electric shaver")

    assert seen == ["leaf", "mid"]
    assert rows[0]["url"] == "https://www.tiktok.com/@bob/video/v9"


def test_api_failure_raises_even_though_http_status_is_200(stub_client):
    """Kalodata reports a rejected key as HTTP 200 with success: false."""
    stub_client({
        "product/rank": {"success": False, "data": None,
                         "message": "The key is not allowed", "code": "501"},
    })
    with pytest.raises(RuntimeError, match="The key is not allowed"):
        k.top_videos("electric shaver")


def _discover_handler(routes: dict[str, dict]):
    """Route category/rank once, product/rank once per category_ids payload.

    Unlike ``_responder`` (routes purely by path), discovery calls
    ``product/rank`` more than once with different bodies, so this keys off
    the request payload's ``category_ids`` too.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/openapi/v1/tiktok/", 1)[-1]
        body = json.loads(request.content)
        assert "keyword" not in body  # discovery must never filter by keyword
        if path == "category/rank":
            return httpx.Response(200, json=routes["category/rank"])
        if path == "product/rank":
            category_id = body["category_ids"][0]
            return httpx.Response(200, json=routes["product/rank"][category_id])
        raise AssertionError(f"unexpected path {path!r}")

    return httpx.MockTransport(handler)


def test_discover_keywords_finds_top_products_across_top_categories(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings.kalodata, "discover_top_categories", 2)
    monkeypatch.setattr(settings.kalodata, "discover_products_per_category", 1)
    transport = _discover_handler({
        "category/rank": {"success": True, "data": [
            {"category_id": "cat-1", "category_name": "Beauty"},
            {"category_id": "cat-2", "category_name": "Electronics"},
        ]},
        "product/rank": {
            "cat-1": {"success": True, "data": [{"product_id": "p1", "product_name": "Nebulizer"}]},
            "cat-2": {"success": True,
                      "data": [{"product_id": "p2", "product_name": "Bluetooth Speaker"}]},
        },
    })
    real_client = httpx.Client
    monkeypatch.setattr(
        k.httpx, "Client", lambda **kw: real_client(**{**kw, "transport": transport}),
    )

    assert k.discover_keywords() == ["Nebulizer", "Bluetooth Speaker"]


def test_discover_keywords_dedupes_a_product_ranked_in_two_categories(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings.kalodata, "discover_top_categories", 2)
    monkeypatch.setattr(settings.kalodata, "discover_products_per_category", 1)
    transport = _discover_handler({
        "category/rank": {"success": True, "data": [
            {"category_id": "cat-1", "category_name": "Beauty"},
            {"category_id": "cat-2", "category_name": "Beauty Sub"},
        ]},
        "product/rank": {
            "cat-1": {"success": True, "data": [{"product_id": "p1", "product_name": "Nebulizer"}]},
            "cat-2": {"success": True, "data": [{"product_id": "p1", "product_name": "Nebulizer"}]},
        },
    })
    real_client = httpx.Client
    monkeypatch.setattr(
        k.httpx, "Client", lambda **kw: real_client(**{**kw, "transport": transport}),
    )

    assert k.discover_keywords() == ["Nebulizer"]
