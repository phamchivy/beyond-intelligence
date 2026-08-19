"""Local embedding via fastembed (ONNX, no torch, no network after the model is cached).

``embedder_model_id`` is part of the retrieval index's primary key, not
metadata -- embeddings from two models are not comparable, and mixing them
degrades retrieval in a way that is very hard to notice and very easy to
prevent. Changing the model means a new index generation and a rebuild,
which is cheap because the index is derived from Silver.
"""

from __future__ import annotations

from functools import lru_cache

from fastembed import TextEmbedding

from lib.settings import settings

MODEL_ID = settings.retrieval.embedder_model_id
DIMENSIONS = 384


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    """Load the embedding model once per process."""
    return TextEmbedding(MODEL_ID)


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the pinned model.

    Args:
        texts: The strings to embed.

    Returns:
        One 384-dimensional vector per input text, in the same order.
    """
    return [vector.tolist() for vector in _model().embed(texts)]
