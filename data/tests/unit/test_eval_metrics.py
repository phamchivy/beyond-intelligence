"""Unit tests for the eval harness's metric functions -- no container, no database."""

from defs.evaluate import _hash_text, _score_arm


def test_f1_on_a_known_hand_computed_case() -> None:
    """One perfect hit and one total miss over two cases gives a hand-verifiable F1."""
    cases = [
        {"case_id": "q1", "expected_chunk_ids": ["c1"]},
        {"case_id": "q2", "expected_chunk_ids": ["c2"]},
    ]
    retrieved = {"q1": ["c1"], "q2": ["c9"]}
    metrics = _score_arm(cases, retrieved, top_k=5)
    assert 0.0 < metrics.f1 < 1.0
    assert metrics.recall_at_k == 0.5


def test_mrr_rewards_earlier_correct_hit() -> None:
    """A correct hit at rank 1 scores a higher MRR than the same hit at rank 3."""
    cases = [{"case_id": "q1", "expected_chunk_ids": ["c1"]}]
    early = _score_arm(cases, {"q1": ["c1", "c2", "c3"]}, top_k=5)
    late = _score_arm(cases, {"q1": ["c2", "c3", "c1"]}, top_k=5)
    assert early.mrr > late.mrr


def test_dataset_version_changes_when_a_label_changes() -> None:
    """Hashing the dataset text means an edited label is never confused with an unchanged one."""
    v1 = _hash_text('{"case_id": "q1", "expected_chunk_ids": ["c1"]}')
    v2 = _hash_text('{"case_id": "q1", "expected_chunk_ids": ["c2"]}')
    assert v1 != v2
