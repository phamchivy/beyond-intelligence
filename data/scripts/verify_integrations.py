"""Stage 0.5: verify the four load-bearing integration points before writing against them.

Run before any of defs/ingest.py, lib/sql.py, or lib/delta.py is trusted:
`python scripts/verify_integrations.py`. Each check prints PASS/FAIL and,
on failure, the named fallback from data-architecture.md §17.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def check_1_dlt_writes_delta() -> tuple[bool, str]:
    """Does dlt's filesystem destination write Delta with table_format='delta'?"""
    import csv

    import dlt
    from dlt.sources.filesystem import filesystem, read_csv

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src"
        src.mkdir()
        with (src / "probe.csv").open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["a", "b"])
            writer.writerow([1, 2])

        dest = Path(tmp) / "dest"
        pipeline = dlt.pipeline("probe", destination=dlt.destinations.filesystem(str(dest)))
        pipeline.run(
            filesystem(bucket_url=str(src), file_glob="*.csv") | read_csv(),
            table_name="probe_table",
            table_format="delta",
        )
        delta_dirs = list(dest.rglob("_delta_log"))
        return bool(delta_dirs), (
            "OK -- dlt wrote a Delta table" if delta_dirs else
            "FAIL -- fallback: dlt writes Parquet to Landing, a Polars step produces Bronze Delta"
        )


def check_2_duckdb_reads_delta() -> tuple[bool, str]:
    """Does DuckDB's delta_scan read a Delta table?"""
    import duckdb
    import pyarrow as pa
    from deltalake import write_deltalake

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t"
        write_deltalake(str(path), pa.table({"id": [1, 2, 3]}))
        con = duckdb.connect()
        con.execute("INSTALL delta; LOAD delta;")
        rows = con.sql(f"SELECT * FROM delta_scan('{path}')").fetchall()
        ok = len(rows) == 3
        return ok, (
            "OK -- delta_scan read the table" if ok else
            "FAIL -- fallback: read with Polars, register the Arrow table into DuckDB"
        )


def check_3_delta_merge_works() -> tuple[bool, str]:
    """Does DeltaTable.merge update rows by key?

    Informational: this build has no MERGE caller (media is excluded).
    """
    import pyarrow as pa
    from deltalake import DeltaTable, write_deltalake

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "m"
        write_deltalake(str(path), pa.table({"id": [1, 2], "v": ["a", "b"]}))
        (
            DeltaTable(str(path))
            .merge(
                pa.table({"id": [2], "v": ["B"]}),
                predicate="t.id = s.id",
                source_alias="s",
                target_alias="t",
            )
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute()
        )
        n = DeltaTable(str(path)).to_pyarrow_table().num_rows
        ok = n == 2
        return ok, (
            "OK -- MERGE updated by key (informational: no caller in this build)" if ok else
            "FAIL -- fallback: reconsider Delta's role without a MERGE caller"
        )


def check_4_dagster_dlt_imports() -> tuple[bool, str]:
    """Does dagster_dlt import with the expected symbols?"""
    try:
        from dagster_dlt import DagsterDltResource, dlt_assets  # noqa: F401

        return True, "OK -- dagster_dlt imports"
    except ImportError as exc:
        return False, f"FAIL -- fallback: call the dlt pipeline inside a plain @asset ({exc})"


def main() -> int:
    """Run all four checks and print a pass/fail line for each."""
    checks = [
        ("1. dlt writes Delta", check_1_dlt_writes_delta),
        ("2. DuckDB reads Delta", check_2_duckdb_reads_delta),
        ("3. DeltaTable.merge works", check_3_delta_merge_works),
        ("4. dagster_dlt imports", check_4_dagster_dlt_imports),
    ]
    all_ok = True
    for label, fn in checks:
        try:
            ok, message = fn()
        except Exception as exc:  # noqa: BLE001 -- this script reports, never crashes silently
            ok, message = False, f"FAIL -- exception: {exc}"
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: {message}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
