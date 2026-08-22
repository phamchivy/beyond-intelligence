"""Unit tests for the RRF fusion behaviour, exercised without a database.

lib.db.search runs the fusion inside SQL, so these tests reimplement the
same rank-fusion arithmetic in Python to pin down its documented
properties independent of a live Postgres connection.
"""

from __future__ import annotations


def _rrf_fuse(
    dense_ranks: dict[str, int], lexical_ranks: dict[str, int], *, rrf_k: int
) -> dict[str, float]:
    """Fuse two rank dicts with Reciprocal Rank Fusion -- mirrors lib.db._HYBRID_SQL."""
    scores: dict[str, float] = {}
    for ranks in (dense_ranks, lexical_ranks):
        for chunk_id, rank in ranks.items():
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def test_item_ranked_first_in_both_legs_wins() -> None:
    """A chunk ranked #1 in both legs outscores one ranked #1 in only one leg."""
    dense = {"a": 1, "b": 2}
    lexical = {"a": 1, "c": 2}
    scores = _rrf_fuse(dense, lexical, rrf_k=60)
    assert scores["a"] > scores["b"]
    assert scores["a"] > scores["c"]


def test_larger_k_flattens_ranking() -> None:
    """A larger rrf_k shrinks the gap between a rank-1 and a rank-2 item."""
    dense = {"a": 1, "b": 2}
    small_k = _rrf_fuse(dense, {}, rrf_k=1)
    large_k = _rrf_fuse(dense, {}, rrf_k=1000)
    gap_small = small_k["a"] - small_k["b"]
    gap_large = large_k["a"] - large_k["b"]
    assert gap_small > gap_large


def test_scores_normalised_to_unit_interval() -> None:
    """Normalising by the max in the returned set puts every score in [0, 1] with one at 1.0."""
    raw = {"a": 0.032, "b": 0.016, "c": 0.008}
    max_score = max(raw.values())
    normalised = {k: v / max_score for k, v in raw.items()}
    assert max(normalised.values()) == 1.0
    assert all(0.0 <= v <= 1.0 for v in normalised.values())
