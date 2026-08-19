"""Fixed chunk-id and text templates (decision 8.11).

These formats appear in the API response, the eval dataset and the logs,
so they must never drift once chosen. Without the media pipeline, only the
document kind is live -- the transcript and frame-caption templates that
architecture §6.6 and decision 8.11 describe are intentionally not written
here, since nothing in this build produces them.
"""

from __future__ import annotations


def document_chunk_id(document_id: str, index: int) -> str:
    """Build a document chunk id: ``{document_id}:document:{index:02d}``.

    Args:
        document_id: The parsed document's stable id.
        index: The chunk's position within the document, 0-based.

    Returns:
        The fixed-format chunk id.
    """
    return f"{document_id}:document:{index:02d}"
