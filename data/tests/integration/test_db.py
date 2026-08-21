"""Integration tests for sql/001_init.sql and lib.db -- needs Postgres running."""

import pytest

from lib import db
from lib.embedding import MODEL_ID, embed

pytestmark = pytest.mark.integration


def test_init_sql_is_idempotent() -> None:
    """Applying 001_init.sql twice produces no error."""
    db.apply_init_sql()
    db.apply_init_sql()


def test_extensions_exist() -> None:
    """vector, pg_trgm and unaccent are all installed."""
    with db.connection() as conn:
        rows = conn.execute(
            "select extname from pg_extension where extname in ('vector','pg_trgm','unaccent')"
        ).fetchall()
    assert {r["extname"] for r in rows} == {"vector", "pg_trgm", "unaccent"}


def test_immutable_unaccent_usable_in_index_expression() -> None:
    """immutable_unaccent can be called inside a query without erroring -- proves it's IMMUTABLE."""
    with db.connection() as conn:
        row = conn.execute("select public.immutable_unaccent('giảm giá') as result").fetchone()
    assert row["result"] == "giam gia"


def test_dump_and_restore_round_trip_a_chunk() -> None:
    """A chunk survives a dump to S3, deletion from Postgres, then a restore from S3."""
    chunk = {
        "chunk_id": "TEST-snapshot-roundtrip",
        "document_id": "TEST-doc",
        "source_type": "document",
        "chunk_index": 0,
        "content": "s3 snapshot round trip fixture",
        "metadata": {"note": "integration test fixture"},
    }
    vector = embed([chunk["content"]])[0]

    try:
        db.upsert_chunks([chunk], [vector], embedder_model_id=MODEL_ID)
        db.dump_index_to_delta()

        with db.connection() as conn:
            conn.execute('delete from "index".chunk where chunk_id = %s', (chunk["chunk_id"],))
            row = conn.execute(
                'select 1 from "index".chunk where chunk_id = %s', (chunk["chunk_id"],)
            ).fetchone()
        assert row is None

        db.restore_index_from_delta()

        with db.connection() as conn:
            row = conn.execute(
                'select content from "index".chunk where chunk_id = %s', (chunk["chunk_id"],)
            ).fetchone()
        assert row["content"] == chunk["content"]
    finally:
        with db.connection() as conn:
            conn.execute('delete from "index".chunk where chunk_id = %s', (chunk["chunk_id"],))
        db.dump_index_to_delta()
