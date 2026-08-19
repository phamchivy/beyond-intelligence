"""Unit tests for the Silver `.sql` files -- what Delta makes possible without a container.

A Delta table is a directory, so a test writes a small one to `tmp_path`,
points a `.sql` file at it, and asserts on the Arrow result.
"""

from __future__ import annotations

import glob
from pathlib import Path

import duckdb
import pyarrow as pa
from deltalake import write_deltalake

_SQL_ROOT = Path(__file__).resolve().parent.parent.parent / "sql" / "transforms"


def _run_sql_against_tmp_bronze(
    tmp_path: Path, sql_file: str, bronze_table: pa.Table, table_name: str
) -> pa.Table:
    """Write a small Bronze Delta fixture and run a Silver `.sql` file against it.

    dlt's filesystem destination nests each table under
    ``<dataset_name>/<table_name>`` -- here both equal ``table_name``,
    matching how defs/ingest.py pins them with ``.with_name(...)`` -- so
    the fixture is written one level deeper than a naive ``bronze/<table>``.
    """
    bronze_path = tmp_path / "bronze" / table_name / table_name
    write_deltalake(str(bronze_path), bronze_table)

    sql_text = (_SQL_ROOT / "silver" / sql_file).read_text().format(bronze=str(tmp_path / "bronze"))
    con = duckdb.connect()
    con.execute("INSTALL delta; LOAD delta;")
    return con.sql(sql_text).to_arrow_table()


def test_stg_orders_dedupes_on_business_key(tmp_path: Path) -> None:
    """Two rows sharing an order_id collapse to the most recent one."""
    bronze = pa.table({
        "order_id": ["ORD-1", "ORD-1", "ORD-2"],
        "customer_id": ["C1", "C1", "C2"],
        "amount": [10.0, 15.0, 20.0],
        "ordered_at": ["2026-08-01T00:00:00", "2026-08-02T00:00:00", "2026-08-01T00:00:00"],
    })
    result = _run_sql_against_tmp_bronze(tmp_path, "stg_erp__orders.sql", bronze, "orders")
    order_1_rows = result.filter(pa.compute.equal(result["order_id"], "ORD-1"))
    assert result.num_rows == 2
    assert order_1_rows.column("amount").to_pylist() == [15.0]


def test_stg_orders_casts_amount(tmp_path: Path) -> None:
    """amount is cast to a float column in the output."""
    bronze = pa.table({
        "order_id": ["ORD-1"], "customer_id": ["C1"], "amount": [10.5],
        "ordered_at": ["2026-08-01T00:00:00"],
    })
    result = _run_sql_against_tmp_bronze(tmp_path, "stg_erp__orders.sql", bronze, "orders")
    assert pa.types.is_floating(result.schema.field("amount").type)


def test_no_select_star_in_any_sql_file() -> None:
    """No `.sql` file under sql/transforms uses `select *` -- explicit columns only."""
    for path in glob.glob(str(_SQL_ROOT / "**" / "*.sql"), recursive=True):
        code_lines = (
            line for line in Path(path).read_text().lower().splitlines()
            if not line.strip().startswith("--")
        )
        code = "\n".join(code_lines)
        assert "select *" not in code, f"{path} uses select * across a layer boundary"
