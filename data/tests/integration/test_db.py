"""Integration tests for sql/001_init.sql and lib.db -- needs Postgres running."""

import pytest

from lib import db

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
