"""Integration test for the PDF pipeline -- needs the tests/fixtures/policy.pdf fixture."""

from pathlib import Path

import pytest
from docling.chunking import HybridChunker

from defs.documents import _CONVERTER

pytestmark = pytest.mark.integration

_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "policy.pdf"


def test_pdf_yields_chunks_and_a_table_survives_as_text() -> None:
    """The fixture PDF yields more than zero chunks, and its table's content survives as text."""
    doc = _CONVERTER.convert(str(_FIXTURE)).document
    chunks = list(HybridChunker().chunk(doc))
    assert len(chunks) > 0

    full_text = " ".join(c.text for c in chunks).lower()
    assert "canh bao" in full_text or "khoa kenh" in full_text
