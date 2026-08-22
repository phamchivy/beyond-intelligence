"""Unit tests for the trending-videos endpoint -- db, embed and rerank are stubbed.

No database, no model download: the hybrid retrieval result and the
cross-encoder scores are both handed in directly.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import api

_DAY = 86_400.0


def _chunk(
    video_id: str, *, revenue: float, age_days: float = 0.0, content: str = "text",
    ad: int = 0, digg_count: int = 0, share_count: int = 0, comment_count: int = 0,
    creator_debut: str | None = None,
) -> dict:
    """One hybrid-retrieval row, shaped as lib.db.search returns it."""
    return {
        "chunk_id": f"VID-{video_id}",
        "document_id": video_id,
        "content": content,
        "score": 0.016,
        "metadata": {
            "video_id": video_id,
            "title": f"title {video_id}",
            "url": f"https://www.tiktok.com/@x/video/{video_id}",
            "category_name": "Body Beauty Devices",
            "product_name": "Nebulizer",
            "matched_keyword": "nebulizer",
            "revenue": revenue,
            "views": 1000,
            "ai_video": 0,
            "ad": ad,
            "digg_count": digg_count,
            "share_count": share_count,
            "comment_count": comment_count,
            "creator_debut": creator_debut,
            "duration_s": 60.0,
            "fetched_at": time.time() - age_days * _DAY,
            "storyboard": {
                "hook": f"hook {video_id}", "cta": "buy", "summary": "s",
                "scenes": [{"scene_no": 0, "t_start": 0.0, "t_end": 1.0, "shot_type": "close-up",
                            "visual": "v", "on_screen_text": "", "voiceover": ""}],
            },
        },
    }


@pytest.fixture(autouse=True)
def _patch_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the real apply_init_sql() call on app startup."""
    monkeypatch.setattr(api.db, "apply_init_sql", lambda: None)
    monkeypatch.setattr(api, "embed", lambda texts: [[0.1, 0.2, 0.3]])


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch):
    """Return a factory pinning db.search results and the rerank scores they get."""
    def install(chunks: list[dict], scores: list[float]) -> TestClient:
        monkeypatch.setattr(api.db, "search", lambda q, qvec, **kw: chunks)
        monkeypatch.setattr(api, "rerank", lambda q, docs: scores)
        return TestClient(api.app)

    return install


def test_returns_the_full_storyboard_not_just_the_matched_text(wire):
    client = wire([_chunk("v1", revenue=100.0)], [5.0])
    item = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"][0]

    assert item["video_id"] == "v1"
    assert item["storyboard"]["hook"] == "hook v1"
    assert len(item["storyboard"]["scenes"]) == 1
    assert item["category_name"] == "Body Beauty Devices"


def test_low_rerank_score_is_outranked_not_dropped_despite_higher_revenue(wire):
    """Rerank reorders (relevance beats revenue), but nothing is removed."""
    client = wire(
        [_chunk("rich_offtopic", revenue=999_999.0), _chunk("relevant", revenue=1.0)],
        [-4.0, 3.0],
    )
    items = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"]

    assert [i["video_id"] for i in items] == ["relevant", "rich_offtopic"]


def test_among_relevant_results_higher_revenue_wins(wire, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api.settings.retrieval, "rerank_min_score", 0.0)
    client = wire(
        [_chunk("small", revenue=10.0), _chunk("big", revenue=5000.0)],
        [1.0, 1.0],
    )
    items = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"]

    assert [i["video_id"] for i in items] == ["big", "small"]


def test_an_older_video_loses_to_a_newer_one_at_equal_revenue(
    wire, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(api.settings.retrieval, "rerank_min_score", 0.0)
    monkeypatch.setattr(api.settings.retrieval, "trending_half_life_days", 14.0)
    client = wire(
        [_chunk("old", revenue=100.0, age_days=60.0), _chunk("new", revenue=100.0, age_days=0.0)],
        [1.0, 1.0],
    )
    items = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"]

    assert [i["video_id"] for i in items] == ["new", "old"]
    assert items[0]["trending_score"] > items[1]["trending_score"]


def test_an_irrelevant_hit_still_returns_with_its_low_rerank_score_visible(wire):
    """No relevance gate yet -- an off-topic query still gets its best hybrid match,
    but the low rerank_score in the response is what a caller filters on itself."""
    client = wire([_chunk("v1", revenue=100.0)], [-9.0])
    resp = client.get("/api/v1/videos/trending", params={"q": "laptop cooling pad"})

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["video_id"] for i in items] == ["v1"]
    assert items[0]["rerank_score"] == -9.0


def test_top_k_defaults_to_five_and_is_clamped_to_max(wire, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api.settings.retrieval, "rerank_min_score", 0.0)
    chunks = [_chunk(f"v{i}", revenue=float(i)) for i in range(10)]
    client = wire(chunks, [1.0] * 10)

    assert len(client.get("/api/v1/videos/trending", params={"q": "x"}).json()["items"]) == 5

    huge = client.get("/api/v1/videos/trending", params={"q": "x", "top_k": 10_000})
    assert len(huge.json()["items"]) == 10  # capped by candidates, never errors


def test_search_is_scoped_to_the_video_source_type(monkeypatch: pytest.MonkeyPatch):
    """Video queries must not compete with the document chunks in the same index."""
    monkeypatch.setattr(api.db, "apply_init_sql", lambda: None)
    monkeypatch.setattr(api, "embed", lambda texts: [[0.1]])
    monkeypatch.setattr(api, "rerank", lambda q, docs: [])
    seen = {}

    def _fake_search(q, qvec, **kw):
        seen.update(kw)
        return []

    monkeypatch.setattr(api.db, "search", _fake_search)
    TestClient(api.app).get("/api/v1/videos/trending", params={"q": "x"})

    assert seen["source_type"] == "video_storyboard"
    assert seen["top_k"] == api.settings.retrieval.candidate_k


def test_get_and_post_return_identical_bodies(wire, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api.settings.retrieval, "rerank_min_score", 0.0)
    client = wire([_chunk("v1", revenue=100.0)], [2.0])

    get_resp = client.get("/api/v1/videos/trending", params={"q": "nebulizer", "top_k": 3})
    post_resp = client.post("/api/v1/videos/trending", json={"q": "nebulizer", "top_k": 3})
    assert get_resp.json() == post_resp.json()


def test_relevance_is_a_calibrated_probability_not_a_raw_logit(wire):
    client = wire([_chunk("garbage", revenue=1.0), _chunk("great", revenue=1.0)], [-9.0, 4.21])
    items = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"]
    by_id = {i["video_id"]: i for i in items}

    assert by_id["garbage"]["rerank_score"] == -9.0
    assert by_id["garbage"]["relevance"] < 0.01
    assert by_id["great"]["rerank_score"] == 4.21
    assert by_id["great"]["relevance"] > 0.95


def test_meta_echoes_the_query_and_states_no_relevance_gate(wire):
    client = wire([_chunk("v1", revenue=100.0)], [1.0])
    body = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()

    assert body["meta"]["query"] == "nebulizer"
    assert body["meta"]["relevance_gated"] is False
    assert body["meta"]["candidates_considered"] == 1


def test_text_field_carries_the_hook_and_every_scene(wire):
    client = wire([_chunk("v1", revenue=100.0)], [1.0])
    item = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"][0]

    assert "hook v1" in item["text"]
    assert "close-up" in item["text"]
    assert item["id"] == "v1"


def test_creator_debut_drives_age_not_fetched_at(wire, monkeypatch: pytest.MonkeyPatch):
    """fetched_at (our download time) must never override a known real publish date."""
    monkeypatch.setattr(api.settings.retrieval, "rerank_min_score", 0.0)
    old_debut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 400 * _DAY))
    client = wire(
        [_chunk("just_fetched", revenue=100.0, creator_debut=old_debut, age_days=0.0)], [1.0],
    )
    item = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"][0]

    assert item["age_days"] > 300  # old by publish date, despite being fetched today


def test_is_ad_and_engagement_rate_surface_from_metadata(wire):
    client = wire(
        [_chunk("v1", revenue=100.0, ad=1, digg_count=50, share_count=30, comment_count=20)],
        [1.0],
    )
    item = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["items"][0]

    assert item["is_ad"] is True
    assert item["engagement_rate"] == 0.1  # (50+30+20)/1000


def test_enrichment_fields_widen_the_embedding_but_never_reach_lexical_search(
    monkeypatch: pytest.MonkeyPatch,
):
    """key_message/audience_profile/product_features must only affect the dense-leg
    embedding text -- db.search's q stays the bare product/category term, since that's
    what the lexical (trigram/ts_rank) leg matches against."""
    embed_calls: list[list[str]] = []
    monkeypatch.setattr(api, "embed", lambda texts: embed_calls.append(texts) or [[0.1, 0.2, 0.3]])
    search_q: list[str] = []

    def _fake_search(q, qvec, **kw):
        search_q.append(q)
        return [_chunk("v1", revenue=100.0)]

    monkeypatch.setattr(api.db, "apply_init_sql", lambda: None)
    monkeypatch.setattr(api.db, "search", _fake_search)
    monkeypatch.setattr(api, "rerank", lambda q, docs: [1.0])

    TestClient(api.app).post("/api/v1/videos/trending", json={
        "q": "portable nebulizer",
        "key_message": "quiet enough for a sleeping baby",
        "audience_profile": "new parents",
        "product_features": "rechargeable, anti-leak cup",
    })

    embedded_text = embed_calls[0][0]
    assert "portable nebulizer" in embedded_text
    assert "quiet enough for a sleeping baby" in embedded_text
    assert "new parents" in embedded_text
    assert "rechargeable, anti-leak cup" in embedded_text
    assert search_q == ["portable nebulizer"]  # never the enriched string


def test_embed_text_is_just_q_when_enrichment_fields_omitted(
    wire, monkeypatch: pytest.MonkeyPatch,
):
    embed_calls: list[list[str]] = []
    monkeypatch.setattr(api, "embed", lambda texts: embed_calls.append(texts) or [[0.1, 0.2, 0.3]])
    client = wire([_chunk("v1", revenue=100.0)], [1.0])
    client.get("/api/v1/videos/trending", params={"q": "nebulizer"})

    assert embed_calls[0] == ["nebulizer"]


def test_meta_echoes_enrichment_fields_including_null_when_omitted(wire):
    client = wire([_chunk("v1", revenue=100.0)], [1.0])

    with_fields = client.get("/api/v1/videos/trending", params={
        "q": "nebulizer", "key_message": "km", "audience_profile": "ap",
        "product_features": "pf",
    }).json()["meta"]
    assert with_fields["key_message"] == "km"
    assert with_fields["audience_profile"] == "ap"
    assert with_fields["product_features"] == "pf"

    without_fields = client.get("/api/v1/videos/trending", params={"q": "nebulizer"}).json()["meta"]
    assert without_fields["key_message"] is None
    assert without_fields["audience_profile"] is None
    assert without_fields["product_features"] is None
