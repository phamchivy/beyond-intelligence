"""Run a `.sql` file against Delta tables with DuckDB, and write the result with Delta.

This module is the function that replaced dbt: eight lines doing what
``dbt-core`` + ``dbt-duckdb`` + ``dagster-dbt`` + three config files did in
version 2.0. DuckDB never writes Delta -- it reads, computes, and returns
Arrow; ``lib.delta`` performs the write, so every write in this layer goes
through one path.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pyarrow as pa

from lib.delta import storage_options, table_uri, write_delta
from lib.settings import settings

_SQL_ROOT = Path(__file__).resolve().parent.parent / "sql" / "transforms"


def read_sql(name: str, **paths: str) -> str:
    """Load a `.sql` file and fill its ``{bronze}`` / ``{silver}`` / ``{gold}`` placeholders.

    SQL files are parameterised by Python, not by a templating language
    (decision 8.18) -- removing dbt removed Jinja, and the moment a
    ``.sql`` file grows a conditional it stops being reviewable as SQL.

    Args:
        name: Path relative to ``sql/transforms/``, e.g.
            ``"silver/stg_erp__orders.sql"``.
        **paths: Values for any ``{bronze}``/``{silver}``/``{gold}``
            placeholders the file uses. Defaults to the current
            ``Settings`` layer URLs when not given.

    Returns:
        The SQL text with placeholders filled in.
    """
    text = (_SQL_ROOT / name).read_text()
    defaults = {
        "bronze": settings.storage.bronze_url,
        "silver": settings.storage.silver_url,
        "gold": settings.storage.gold_url,
    }
    return text.format(**{**defaults, **paths})


def _connect() -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection configured to read Delta tables over S3/MinIO."""
    con = duckdb.connect()
    con.execute("INSTALL delta; LOAD delta; INSTALL httpfs; LOAD httpfs;")
    opts = storage_options()
    con.execute(f"""
        CREATE SECRET (
            TYPE s3,
            ENDPOINT '{opts["AWS_ENDPOINT_URL"].removeprefix("http://").removeprefix("https://")}',
            KEY_ID '{opts["AWS_ACCESS_KEY_ID"]}',
            SECRET '{opts["AWS_SECRET_ACCESS_KEY"]}',
            USE_SSL false,
            URL_STYLE 'path'
        )
    """)
    return con


def duckdb_arrow(sql: str) -> pa.Table:
    """Run a SQL statement against Delta tables and return an Arrow table.

    Args:
        sql: The SQL text to run, already filled in by :func:`read_sql`.

    Returns:
        The query result as a PyArrow table.
    """
    con = _connect()
    try:
        # to_arrow_table(), not .arrow() -- DuckDB 1.5's .arrow() returns a
        # RecordBatchReader, not a Table, which silently breaks every
        # .num_rows / column-access call downstream.
        return con.sql(sql).to_arrow_table()
    finally:
        con.close()


def run_sql_to_delta(
    sql: str, layer: str, name: str, *, mode: str = "overwrite"
) -> tuple[pa.Table, int]:
    """Run a SQL file against Delta tables and write the result to a Delta table.

    Args:
        sql: The SQL text to run.
        layer: The destination layer, e.g. ``"silver"``.
        name: The destination dataset name.
        mode: ``"overwrite"`` or ``"append"``, passed through to
            :func:`lib.delta.write_delta`.

    Returns:
        A tuple of the resulting Arrow table and the Delta commit version
        the write produced -- the caller can validate before or after the
        write with the same table.
    """
    table = duckdb_arrow(sql)
    version = write_delta(layer, name, table, mode=mode)
    return table, version


__all__ = ["read_sql", "duckdb_arrow", "run_sql_to_delta", "table_uri"]
