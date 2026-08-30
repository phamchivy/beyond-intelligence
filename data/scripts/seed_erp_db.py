"""Seed the `source` Postgres schema that stands in for an external ERP database.

Run once before stage 3, from `data/`: `python -m scripts.seed_erp_db`.
"""

from __future__ import annotations

import random

from lib import db

random.seed(7)
_COUNTRIES = ["VN", "US", "SG", "TH", "ID"]


def seed() -> None:
    """Insert ~50 customers into source.customers."""
    with db.connection() as conn:
        conn.execute("TRUNCATE source.customers CASCADE")
        rows = [
            (f"CUST-{i:03d}", f"Customer {i}", random.choice(_COUNTRIES))
            for i in range(1, 51)
        ]
        conn.cursor().executemany(
            "INSERT INTO source.customers (customer_id, name, country) VALUES (%s, %s, %s)", rows
        )
    print(f"seeded {len(rows)} rows into source.customers")


if __name__ == "__main__":
    seed()
