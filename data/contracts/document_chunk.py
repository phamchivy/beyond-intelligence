"""Contract for parsed document chunks -- sourced from the PDF pipeline."""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series

CONTRACT_VERSION = "document_chunk-v1"


class DocumentChunkSchema(pa.DataFrameModel):
    """Silver-layer contract for `document_chunk`."""

    chunk_id: Series[str] = pa.Field(unique=True)
    document_id: Series[str]
    chunk_index: Series[int] = pa.Field(ge=0)
    content: Series[str] = pa.Field(str_length=(1, None))
