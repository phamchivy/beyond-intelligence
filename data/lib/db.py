"""Postgres access: psycopg helpers called directly, no repository class.

A handful of queries does not earn an abstraction layer. Every function
here is a plain function over a plain connection.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from lib.settings import settings


@contextmanager
def connection(*, dsn: str | None = None) -> Iterator[psycopg.Connection]:
    """Open a Postgres connection as a context manager.

    Args:
        dsn: Connection string. Defaults to ``settings.database.url``.

    Yields:
        An open ``psycopg.Connection`` with dict-row results, committed on
        clean exit and rolled back on exception.
    """
    conn = psycopg.connect(dsn or settings.database.url, row_factory=dict_row)
    # Without this, a Python list is sent as a plain array and pgvector's
    # <=> operator has no match for `vector <=> double precision[]`.
    register_vector(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_init_sql() -> None:
    """Apply ``sql/001_init.sql``. Safe to call on every API startup -- idempotent by design."""
    sql_path = Path(__file__).resolve().parent.parent / "sql" / "001_init.sql"
    with connection() as conn:
        conn.execute(sql_path.read_text())


# ============================================================ ops.run_log


def log_run(*, run_id: str, asset_key: str, pipeline: str, dataset: str | None = None) -> None:
    """Insert a 'running' row into ops.run_log.

    Args:
        run_id: The caller-generated run id (decision 8.13) -- never
            generated inside a pipeline function.
        asset_key: The Dagster asset key, or a route name for API-driven runs.
        pipeline: A short pipeline name, e.g. ``"csv_to_gold"``.
        dataset: The dataset this run concerns, if applicable.
    """
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO ops.run_log (run_id, asset_key, pipeline, dataset, status)
            VALUES (%s, %s, %s, %s, 'running')
            ON CONFLICT (run_id, asset_key) DO NOTHING
            """,
            (run_id, asset_key, pipeline, dataset),
        )


def finish_run(
    *,
    run_id: str,
    asset_key: str,
    status: str,
    rows_in: int = 0,
    rows_out: int = 0,
    rows_rejected: int = 0,
    duration_ms: int | None = None,
    delta_version: int | None = None,
    error_code: str | None = None,
) -> None:
    """Mark a run as succeeded or failed with its final row counts.

    Args:
        run_id: The run id used in the matching :func:`log_run` call.
        asset_key: The asset key used in the matching :func:`log_run` call.
        status: ``"succeeded"`` or ``"failed"``.
        rows_in: Rows read from the upstream layer.
        rows_out: Rows written to the destination layer.
        rows_rejected: Rows quarantined.
        duration_ms: Wall-clock duration of the run.
        delta_version: The Delta commit version this run produced.
        error_code: A short error code when ``status`` is ``"failed"``.
    """
    with connection() as conn:
        conn.execute(
            """
            UPDATE ops.run_log
            SET status = %s, rows_in = %s, rows_out = %s, rows_rejected = %s,
                duration_ms = %s, delta_version = %s, error_code = %s, finished_at = now()
            WHERE run_id = %s AND asset_key = %s
            """,
            (status, rows_in, rows_out, rows_rejected, duration_ms, delta_version,
             error_code, run_id, asset_key),
        )


def record_violation(
    *,
    run_id: str,
    dataset: str,
    contract_version: str,
    check_name: str,
    violation_code: str,
    failure_count: int,
    quarantine_table: str,
    column_name: str | None = None,
    detail: str | None = None,
) -> None:
    """Insert a quality-violation record. ``detail`` must never carry a row payload.

    Args:
        run_id: The run that produced this violation.
        dataset: The dataset name.
        contract_version: The contract version the rows failed against.
        check_name: The Pandera check name that failed.
        violation_code: A short machine-readable code.
        failure_count: Number of rows this violation covers.
        quarantine_table: The Delta table path the rejected rows went to.
        column_name: The offending column, if applicable.
        detail: A short human-readable note -- never the row's own data.
    """
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO ops.quality_violations
                (run_id, dataset, contract_version, check_name, column_name,
                 violation_code, failure_count, quarantine_table, detail)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (run_id, dataset, contract_version, check_name, column_name,
             violation_code, failure_count, quarantine_table, detail),
        )


def record_schema_drift(
    *, run_id: str, dataset: str, change_type: str, column_name: str,
    from_type: str | None = None, to_type: str | None = None,
) -> None:
    """Record a Bronze schema-drift event -- never silently drop an unknown column.

    Args:
        run_id: The run that observed the drift.
        dataset: The dataset name.
        change_type: One of ``column_added``, ``column_removed``, ``type_changed``.
        column_name: The affected column.
        from_type: The previous type, if applicable.
        to_type: The new type, if applicable.
    """
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO ops.schema_drift
                (run_id, dataset, change_type, column_name, from_type, to_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (run_id, dataset, change_type, column_name, from_type, to_type),
        )


# ============================================================ retrieval index


def upsert_chunks(
    chunks: list[dict[str, Any]], embeddings: list[list[float]], *, embedder_model_id: str
) -> None:
    """Upsert chunk text and its embedding into the retrieval index.

    Args:
        chunks: One dict per chunk with keys ``chunk_id``, ``document_id``,
            ``source_type``, ``chunk_index``, ``content``, and optional
            ``metadata``.
        embeddings: One embedding vector per chunk, same order as ``chunks``.
        embedder_model_id: The model id these embeddings came from.
    """
    with connection() as conn:
        for chunk, vector in zip(chunks, embeddings, strict=True):
            conn.execute(
                """
                INSERT INTO "index".chunk
                    (chunk_id, document_id, source_type, chunk_index, content, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content, metadata = EXCLUDED.metadata
                """,
                (chunk["chunk_id"], chunk["document_id"], chunk["source_type"],
                 chunk["chunk_index"], chunk["content"], json.dumps(chunk.get("metadata", {}))),
            )
            conn.execute(
                """
                INSERT INTO "index".embedding
                    (chunk_id, embedder_model_id, dimensions, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (chunk_id, embedder_model_id)
                    DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                (chunk["chunk_id"], embedder_model_id, len(vector), vector),
            )


# ============================================================ hybrid retrieval (architecture §10)

_HYBRID_SQL = """
with dense as (
    select e.chunk_id, row_number() over (order by e.embedding <=> %(qvec)s::vector) as rank
    from "index".embedding e
    join "index".chunk c using (chunk_id)
    where e.embedder_model_id = %(model)s
      and (%(source_type)s::text is null or c.source_type = %(source_type)s)
    order by e.embedding <=> %(qvec)s::vector limit %(leg_k)s
),
lexical as (
    select chunk_id, row_number() over (order by score desc) as rank
    from (
        select chunk_id,
               greatest(
                   similarity(public.immutable_unaccent(content), public.immutable_unaccent(%(q)s)),
                   ts_rank(content_tsv, plainto_tsquery('simple', public.immutable_unaccent(%(q)s)))
               ) as score
        from "index".chunk
        where (%(source_type)s::text is null or source_type = %(source_type)s)
    ) s where score > %(threshold)s
    order by score desc limit %(leg_k)s
)
select c.chunk_id, c.document_id, c.content, c.metadata,
       sum(1.0 / (%(rrf_k)s + r.rank)) as score
from (select * from dense union all select * from lexical) r
join "index".chunk c using (chunk_id)
group by 1,2,3,4 order by score desc limit %(top_k)s
"""


def search(
    q: str, qvec: list[float], *, top_k: int, leg_k: int | None = None,
    rrf_k: int | None = None, threshold: float | None = None, model: str | None = None,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    """Run the hybrid dense + lexical retrieval query, fused with Reciprocal Rank Fusion.

    Dense-only retrieval misses exact identifiers, rare tokens and
    misspellings; lexical-only misses paraphrase. Both legs run and their
    **ranks** (not scores) are fused, which is why no cross-scale
    calibration between the two legs is needed.

    Args:
        q: The raw query text.
        qvec: The query's embedding vector, same model as the index.
        top_k: Maximum number of fused results to return.
        leg_k: Candidates considered per leg before fusion. Defaults to
            ``settings.retrieval.leg_k``.
        rrf_k: The RRF smoothing constant. Defaults to
            ``settings.retrieval.rrf_k``.
        threshold: Minimum lexical score to consider a candidate. Defaults
            to ``settings.retrieval.trigram_threshold``.
        model: The embedder model id to filter the dense leg on. Defaults
            to ``settings.retrieval.embedder_model_id``.
        source_type: Restrict both legs to one ``index.chunk.source_type``,
            e.g. ``"video_storyboard"``. ``None`` searches everything --
            the index holds more than one kind of content, and a caller
            after videos must not compete with document chunks.

    Returns:
        Rows with ``chunk_id``, ``document_id``, ``content``, ``metadata``,
        ``score`` -- ``score`` is raw RRF, not yet normalised to ``[0,1]``
        (that normalisation is presentation-only and happens in ``api.py``).
    """
    with connection() as conn:
        rows = conn.execute(
            _HYBRID_SQL,
            {
                "q": q,
                "qvec": qvec,
                "top_k": top_k,
                "leg_k": leg_k or settings.retrieval.leg_k,
                "rrf_k": rrf_k or settings.retrieval.rrf_k,
                "threshold": (
                    threshold if threshold is not None else settings.retrieval.trigram_threshold
                ),
                "model": model or settings.retrieval.embedder_model_id,
                "source_type": source_type,
            },
        ).fetchall()
    return list(rows)


def search_dense_only(
    q: str, qvec: list[float], *, top_k: int, model: str | None = None
) -> list[dict[str, Any]]:
    """The dense-leg-only retrieval arm, used as an eval baseline.

    Args:
        q: The raw query text (unused, kept for signature symmetry with
            :func:`search`).
        qvec: The query's embedding vector.
        top_k: Maximum results to return.
        model: The embedder model id to filter on.

    Returns:
        Rows ranked purely by cosine distance, same shape as :func:`search`.
    """
    with connection() as conn:
        rows = conn.execute(
            """
            select chunk_id, document_id, content, metadata,
                   1.0 / (1 + (embedding <=> %(qvec)s::vector)) as score
            from "index".embedding e join "index".chunk c using (chunk_id)
            where embedder_model_id = %(model)s
            order by embedding <=> %(qvec)s::vector limit %(top_k)s
            """,
            {
                "qvec": qvec,
                "model": model or settings.retrieval.embedder_model_id,
                "top_k": top_k,
            },
        ).fetchall()
    return list(rows)


def search_lexical_only(
    q: str, *, top_k: int, threshold: float | None = None
) -> list[dict[str, Any]]:
    """The lexical-leg-only retrieval arm, used as an eval baseline.

    Args:
        q: The raw query text.
        top_k: Maximum results to return.
        threshold: Minimum lexical score to consider a candidate.

    Returns:
        Rows ranked purely by trigram/tsvector score, same shape as
        :func:`search`.
    """
    with connection() as conn:
        rows = conn.execute(
            """
            select chunk_id, document_id, content, metadata, score
            from (
                select chunk_id, document_id, content, metadata,
                       greatest(
                           similarity(
                               public.immutable_unaccent(content), public.immutable_unaccent(%(q)s)
                           ),
                           ts_rank(
                               content_tsv,
                               plainto_tsquery('simple', public.immutable_unaccent(%(q)s))
                           )
                       ) as score
                from "index".chunk
            ) s where score > %(threshold)s
            order by score desc limit %(top_k)s
            """,
            {
                "q": q,
                "threshold": (
                    threshold if threshold is not None else settings.retrieval.trigram_threshold
                ),
                "top_k": top_k,
            },
        ).fetchall()
    return list(rows)


def chunk_count() -> int:
    """Return the number of indexed chunks, for the /health response."""
    with connection() as conn:
        row = conn.execute('select count(*) as n from "index".chunk').fetchone()
    return row["n"]


# ============================================================ eval


def record_eval_run(
    *, run_id: str, dataset_version: str, pipeline_version: str, arm: str, n_cases: int,
    precision: float, recall: float, f1: float, recall_at_k: float, mrr: float, report_path: str,
) -> None:
    """Insert one (run, arm) row into ops.eval_run.

    Args:
        run_id: The evaluation run id.
        dataset_version: Hash of the labeled dataset used.
        pipeline_version: Hash of the retrieval configuration used.
        arm: One of ``lexical_only``, ``dense_only``, ``hybrid_rrf``.
        n_cases: Number of labeled cases scored.
        precision: Precision over the cases.
        recall: Recall over the cases.
        f1: F1 over the cases.
        recall_at_k: Recall at the configured top_k.
        mrr: Mean reciprocal rank.
        report_path: Path to the generated Markdown report.
    """
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO ops.eval_run
                (run_id, dataset_version, pipeline_version, arm, n_cases,
                 precision, recall, f1, recall_at_k, mrr, report_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (run_id, dataset_version, pipeline_version, arm, n_cases,
             precision, recall, f1, recall_at_k, mrr, report_path),
        )
