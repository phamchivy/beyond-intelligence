"""Integration tests for the hybrid retrieval query -- needs Postgres and an indexed document."""

import pytest

from lib import db
from lib.embedding import embed

pytestmark = pytest.mark.integration


def test_matches_across_missing_diacritics() -> None:
    """'giam gia' (no diacritics) retrieves the chunk with 'giảm giá' -- Vietnamese mitigation."""
    qvec = embed(["giam gia"])[0]
    results = db.search("giam gia", qvec, top_k=5)
    assert any("giá" in r["content"].lower() or "gia" in r["content"].lower() for r in results)


def test_hybrid_returns_an_item_only_one_leg_found() -> None:
    """A rare-token exact match found only by the lexical leg still appears in the fused result."""
    qvec = embed(["Seller Center"])[0]
    results = db.search("Seller Center", qvec, top_k=5)
    assert any("seller center" in r["content"].lower() for r in results)


def test_hnsw_index_is_used() -> None:
    """The dense leg's query plan uses the HNSW index, not a sequential scan."""
    qvec = embed(["test query"])[0]
    with db.connection() as conn:
        rows = conn.execute(
            'explain select chunk_id from "index".embedding '
            "order by embedding <=> %s::vector limit 5",
            (qvec,),
        ).fetchall()
    plan = " ".join(r["QUERY PLAN"] for r in rows).lower()
    assert "hnsw" in plan or "index scan" in plan
