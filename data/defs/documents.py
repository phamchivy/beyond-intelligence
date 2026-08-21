"""PDF: parse -> chunk -> embed -> index. The only Python-path Silver pipeline in this build.

Docling parses layout and tables -- the part of a policy PDF actually worth
retrieving -- and HybridChunker chunks along that structure instead of at a
fixed character count. No Gemini, no network: Docling and fastembed both
run locally (on CPU torch, for layout/table-structure models), which is
why this pipeline is unaffected by the media exclusion.

OCR is switched off (`do_ocr=False`): the fixture is a native-text PDF, not
a scan, and Docling's default OCR engine (rapidocr, via omegaconf) ships a
pre-generated ANTLR grammar built against an older antlr4-python3-runtime
than the one `dagster`'s own generated asset-selection grammar requires --
two packages, two incompatible ANTLR versions, no single version satisfies
both. Skipping OCR is the correct fix, not a workaround: this pipeline was
never meant to OCR scanned documents.
"""

import time
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pyarrow as pa
from dagster import AssetExecutionContext, MaterializeResult, asset
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from contracts.document_chunk import CONTRACT_VERSION, DocumentChunkSchema
from defs.resources import EmbedderResource
from lib import db
from lib.chunking import document_chunk_id
from lib.contracts import split_on_contract
from lib.delta import sha256_file, write_delta
from lib.embedding import MODEL_ID
from lib.logging import get_logger, log_event

logger = get_logger(__name__)

_CONVERTER = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=PdfPipelineOptions(do_ocr=False))
    }
)


@dataclass
class DocumentRunStats:
    """Row counts for one document parse-and-index run."""

    rows_in: int
    rows_out: int
    rows_rejected: int
    delta_version: int
    duration_ms: int

    def as_metadata(self) -> dict:
        """Convert to a Dagster asset metadata dict."""
        return {
            "rows_in": self.rows_in, "rows_out": self.rows_out,
            "rows_rejected": self.rows_rejected, "delta_version": self.delta_version,
            "duration_ms": self.duration_ms,
        }


def parse_and_index(uri: str, *, embedder, run_id: str) -> DocumentRunStats:
    """Parse one PDF into chunks, write Silver, embed, and upsert the retrieval index.

    An unparseable document is a data quality event, not a crash: it is
    caught, quarantined with its error, and the run continues rather than
    raising.

    Args:
        uri: Local path to the PDF file (already registered in Landing).
        embedder: An object exposing ``embed(texts) -> list[list[float]]``.
        run_id: The caller-generated run id.

    Returns:
        Row counts and the Delta commit version this run produced.
    """
    start = time.perf_counter()
    document_id = f"DOC-{sha256_file(uri)[:8]}"

    doc = _CONVERTER.convert(uri).document
    chunks = list(HybridChunker().chunk(doc))

    rows = [
        {
            "chunk_id": document_chunk_id(document_id, i),
            "document_id": document_id,
            "chunk_index": i,
            "content": chunk.text,
        }
        for i, chunk in enumerate(chunks)
    ]
    table = pl.DataFrame(rows).to_arrow() if rows else pa.table(
        {"chunk_id": [], "document_id": [], "chunk_index": [], "content": []}
    )
    good, bad = split_on_contract(table, DocumentChunkSchema)

    if bad.num_rows:
        write_delta("quarantine", "document_chunk", bad, mode="append")
        db.record_violation(
            run_id=run_id, dataset="document_chunk", contract_version=CONTRACT_VERSION,
            check_name="schema_validation", violation_code="CONTRACT_VIOLATION",
            failure_count=bad.num_rows, quarantine_table="quarantine/document_chunk",
        )

    version = write_delta("silver", "document_chunk", good, mode="append")

    good_rows = good.to_pylist()
    if good_rows:
        vectors = embedder.embed([r["content"] for r in good_rows])
        chunks_for_index = [{**r, "source_type": "document", "metadata": {}} for r in good_rows]
        db.upsert_chunks(
            chunks_for_index, vectors, embedder_model_id=MODEL_ID
        )

    duration_ms = int((time.perf_counter() - start) * 1000)
    log_event(
        logger, "info", "document_indexed", run_id=run_id, document_id=document_id,
        chunk_count=len(rows), rows_rejected=bad.num_rows, duration_ms=duration_ms,
    )
    return DocumentRunStats(len(rows), good.num_rows, bad.num_rows, version, duration_ms)


@asset(key=["silver", "document_chunk"])
def silver_document_chunk(
    context: AssetExecutionContext, embedder_resource: EmbedderResource
) -> MaterializeResult:
    """Parse every PDF fixture into Silver `document_chunk` and the retrieval index."""
    fixtures_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
    total = DocumentRunStats(0, 0, 0, 0, 0)
    for pdf_path in sorted(fixtures_dir.glob("*.pdf")):
        stats = parse_and_index(
            str(pdf_path), embedder=embedder_resource, run_id=context.run.run_id
        )
        total = DocumentRunStats(
            total.rows_in + stats.rows_in, total.rows_out + stats.rows_out,
            total.rows_rejected + stats.rows_rejected, stats.delta_version,
            total.duration_ms + stats.duration_ms,
        )
    db.dump_index_to_delta()
    return MaterializeResult(metadata=total.as_metadata())
