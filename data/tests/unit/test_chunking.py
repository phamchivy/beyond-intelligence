"""Unit tests for lib.chunking -- the fixed chunk-id template."""

from lib.chunking import document_chunk_id


def test_document_chunk_id_format() -> None:
    """Format is `{document_id}:document:{index:02d}` -- fixed, not incidental."""
    assert document_chunk_id("DOC-abc123", 3) == "DOC-abc123:document:03"


def test_reindexing_produces_identical_chunk_ids() -> None:
    """The same document id and index always produce the same chunk id, so re-indexing upserts."""
    first = document_chunk_id("DOC-abc123", 0)
    second = document_chunk_id("DOC-abc123", 0)
    assert first == second
