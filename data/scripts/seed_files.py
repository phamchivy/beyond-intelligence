"""Generate the CSV and XLSX seed files that stand in for real uploaded sources.

Run once before stage 2/3: `python scripts/seed_files.py`. Deliberately
plants malformed rows in `orders.csv` so the quarantine path (architecture
§8) has something real to catch.
"""

from __future__ import annotations

import csv
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

_ROOT = Path(__file__).resolve().parent.parent / "seeds"
_CLASSIFICATIONS = ["public", "internal", "confidential", "pii"]
_COUNTRIES = ["VN", "US", "SG", "TH", "ID"]
_CATEGORIES = ["beauty", "apparel", "electronics", "home", "toys"]

random.seed(42)


def _write_orders_csv() -> None:
    """Write orders_2026-08-01.csv: ~200 rows across 3 files, 3+ deliberately malformed."""
    out_dir = _ROOT / "csv"
    out_dir.mkdir(parents=True, exist_ok=True)

    base = datetime(2026, 8, 1, tzinfo=UTC)
    files = ["orders_2026-08-01.csv", "orders_2026-08-02.csv", "orders_2026-08-03.csv"]
    order_seq = 1

    for file_idx, filename in enumerate(files):
        rows = []
        for _ in range(65):
            order_id = f"ORD-{order_seq:05d}"
            order_seq += 1
            customer_id = f"CUST-{random.randint(1, 50):03d}"
            amount = round(random.uniform(5, 500), 2)
            ordered_at = (base + timedelta(days=file_idx, hours=random.randint(0, 23))).isoformat()
            classification = random.choice(_CLASSIFICATIONS)
            rows.append([order_id, customer_id, amount, ordered_at, classification])

        # Deliberately malformed rows -- the quarantine proof (Gate 2).
        # IDs are unique per file so the Silver `qualify` dedupe (same
        # order_id -> most recent wins) never collapses two malformed rows
        # into one before the contract even sees them. `classification` is
        # not tested here -- stg_erp__orders.sql hardcodes it to
        # 'confidential' regardless of source (architecture §13: PII
        # tagging is applied at landing, never taken from the source), so a
        # bad value in the CSV would silently pass and never reach
        # quarantine.
        rows.append([f"BAD-ID-{file_idx}", "CUST-001", 42.0, base.isoformat(), "public"])
        # negative amount
        rows.append([f"ORD-{order_seq:05d}", "CUST-002", -10.0, base.isoformat(), "public"])
        order_seq += 1
        # bad shape again, distinct id
        rows.append([f"BAD-SHAPE-{file_idx}", "CUST-003", 20.0, base.isoformat(), "public"])

        with (out_dir / filename).open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["order_id", "customer_id", "amount", "ordered_at", "classification"])
            writer.writerows(rows)

    print(f"wrote {len(files)} CSV files to {out_dir}")


def _write_catalog_xlsx() -> None:
    """Write catalog.xlsx: one sheet, ~50 products."""
    out_dir = _ROOT / "xlsx"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        {
            "sku": f"SKU-{i:04d}",
            "product_name": f"Product {i}",
            "price": round(random.uniform(3, 300), 2),
            "category": random.choice(_CATEGORIES),
        }
        for i in range(1, 51)
    ]
    pl.DataFrame(rows).write_excel(out_dir / "catalog.xlsx", worksheet="Sheet1")
    print(f"wrote catalog.xlsx to {out_dir}")


if __name__ == "__main__":
    _write_orders_csv()
    _write_catalog_xlsx()
