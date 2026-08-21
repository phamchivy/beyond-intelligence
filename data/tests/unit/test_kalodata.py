"""Unit tests for scripts/kalodata_top_videos.py -- httpx is stubbed, no network."""

from __future__ import annotations

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


def test_top_videos_resolves_keyword_to_category_then_ranks(stub_client):
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


def test_top_videos_falls_back_to_a_broader_category_when_the_leaf_is_empty(stub_client):
    """A leaf category with no ranked videos must not end the search."""
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
        category = request.read().decode()
        seen.append("leaf" if '"leaf"' in category else "mid")
        data = [] if "leaf" in seen[-1] else [
            {"video_id": "v9", "belonged_creator_handle": "bob", "revenue": 5.0}
        ]
        return httpx.Response(200, json={"success": True, "data": data})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    k.httpx.Client = lambda **kwargs: real_client(**{**kwargs, "transport": transport})
    try:
        rows = k.top_videos("electric shaver")
    finally:
        k.httpx.Client = real_client

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
