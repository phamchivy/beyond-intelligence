"""Unit tests for lib.contracts.split_on_contract -- no container, no network."""

import pyarrow as pa

from contracts.orders import OrdersSchema
from lib.contracts import split_on_contract


def _make_table(rows: list[dict]) -> pa.Table:
    return pa.Table.from_pylist(rows)


def test_valid_rows_pass_through() -> None:
    """Every row satisfying the contract ends up in `valid`, none in `rejected`."""
    rows = [
        {"order_id": "ORD-001", "customer_id": "CUST-1", "amount": 10.0,
         "event_date": "2026-08-01", "classification": "public"},
        {"order_id": "ORD-002", "customer_id": "CUST-2", "amount": 20.0,
         "event_date": "2026-08-01", "classification": "internal"},
    ]
    valid, rejected = split_on_contract(_make_table(rows), OrdersSchema)
    assert valid.num_rows == 2
    assert rejected.num_rows == 0


def test_rejected_rows_land_in_quarantine() -> None:
    """A row violating the contract goes to `rejected`, not silently dropped."""
    rows = [
        {"order_id": "ORD-001", "customer_id": "CUST-1", "amount": 10.0,
         "event_date": "2026-08-01", "classification": "public"},
        {"order_id": "BAD-ID", "customer_id": "CUST-2", "amount": -5.0,
         "event_date": "2026-08-01", "classification": "top-secret"},
    ]
    valid, rejected = split_on_contract(_make_table(rows), OrdersSchema)
    assert valid.num_rows == 1
    assert rejected.num_rows == 1
    assert rejected.to_pylist()[0]["order_id"] == "BAD-ID"


def test_lazy_reports_every_violation() -> None:
    """A row violating the contract in multiple ways is still caught in one pass."""
    rows = [{"order_id": "BAD", "customer_id": "CUST-1", "amount": -1.0,
             "event_date": "2026-08-01", "classification": "unknown"}]
    valid, rejected = split_on_contract(_make_table(rows), OrdersSchema)
    assert valid.num_rows == 0
    assert rejected.num_rows == 1
