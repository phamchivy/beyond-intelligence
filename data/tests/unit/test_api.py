"""Unit tests for api.py -- lib.db and lib.embedding are monkeypatched, no network or database."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture(autouse=True)
def _patch_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the real apply_init_sql() call on app startup."""
    monkeypatch.setattr(api.db, "apply_init_sql", lambda: None)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A TestClient with lib.db.search and lib.embedding.embed stubbed out."""
    monkeypatch.setattr(api, "embed", lambda texts: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr(
        api.db, "search",
        lambda q, qvec, *, top_k: [
            {"chunk_id": "DOC-1:document:00", "content": "some text",
             "score": 0.032, "metadata": {}}
        ][:top_k],
    )
    return TestClient(api.app)


def test_get_and_post_return_identical_bodies(client: TestClient) -> None:
    """GET and POST /api/v1/data/query return the same body for the same query (decision 8.5)."""
    get_resp = client.get("/api/v1/data/query", params={"q": "test", "top_k": 3})
    post_resp = client.post("/api/v1/data/query", json={"q": "test", "top_k": 3})
    assert get_resp.json() == post_resp.json()


def test_top_k_clamped_to_max(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A top_k above the configured max is clamped before it reaches the query."""
    seen = {}

    def _fake_search(q, qvec, *, top_k):
        seen["top_k"] = top_k
        return []

    monkeypatch.setattr(api.db, "search", _fake_search)
    client.get("/api/v1/data/query", params={"q": "x", "top_k": 10_000})
    assert seen["top_k"] == api.settings.retrieval.max_top_k


def test_degraded_when_db_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """/health returns 200 with status='degraded' rather than a 5xx when the database is down."""
    monkeypatch.setattr(api.db, "apply_init_sql", lambda: None)

    def _raise():
        raise ConnectionError("db down")

    monkeypatch.setattr(api.db, "chunk_count", _raise)
    client = TestClient(api.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"
    assert resp.json()["db"] is False


def test_scores_normalised_to_unit_interval(client: TestClient) -> None:
    """The single returned item's score is normalised to 1.0 (max-of-set)."""
    resp = client.get("/api/v1/data/query", params={"q": "test", "top_k": 3})
    items = resp.json()["items"]
    assert items[0]["score"] == 1.0
