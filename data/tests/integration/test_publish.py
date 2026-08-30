"""Integration tests for defs.publish -- needs Postgres running and Gold materialized."""

import psycopg
import pytest

from lib.settings import settings

pytestmark = pytest.mark.integration


def test_backend_reader_can_read_api_views_but_not_gold_tables() -> None:
    """The serving boundary is a real Postgres denial, not just a convention (architecture §9)."""
    with psycopg.connect(settings.database.backend_reader_url) as conn:
        rows = conn.execute("select count(*) from api.v1_order_daily").fetchall()
        assert rows[0][0] >= 0

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute('select * from gold."fct_order"').fetchall()
