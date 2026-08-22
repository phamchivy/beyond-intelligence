"""Local cross-encoder reranking via fastembed (ONNX, no torch, no network after caching).

Hybrid retrieval fuses *ranks* (lib/db.py::search), so it knows a chunk
placed well in both legs but nothing about whether its text actually
answers the query -- and an RRF score has no absolute scale to threshold
against. A cross-encoder reads the query and the document together and
returns a score that does, which is what makes a relevance cutoff possible.

Mirrors ``lib/embedding.py``: one pinned model id from settings, loaded
once per process.
"""

from __future__ import annotations

from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from lib.settings import settings

MODEL_ID = settings.retrieval.reranker_model_id


@lru_cache(maxsize=1)
def _model() -> TextCrossEncoder:
    """Load the reranking model once per process."""
    return TextCrossEncoder(MODEL_ID)


def rerank(query: str, documents: list[str]) -> list[float]:
    """Score each document against the query with the pinned cross-encoder.

    Args:
        query: The raw query text.
        documents: Candidate texts, typically ``content`` from a hybrid
            retrieval pass.

    Returns:
        One relevance score per document, in the same order. Scores are
        raw logits -- higher is more relevant, but the scale is
        model-specific and not comparable across reranker models.
    """
    if not documents:
        return []
    return list(_model().rerank(query, documents))
