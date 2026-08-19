"""Integration tests proving each of the four tabular sources produces Landing and Bronze Delta.

Needs docker compose up, seeds generated (scripts/seed_files.py,
scripts/seed_erp_db.py), and the mock API running
(uvicorn scripts.mock_channel_api:app --port 8099).

Each table path is nested twice -- dlt's filesystem destination writes
under ``<dataset_name>/<table_name>``, and defs/ingest.py pins both to the
entity name via ``.with_name(...)`` / ``table_names=[...]``, giving
``bronze/<entity>/<entity>``.
"""

import pytest

from lib.delta import read_delta

pytestmark = pytest.mark.integration


def test_orders_csv_produces_readable_bronze() -> None:
    """After materializing orders_csv_assets, bronze/orders/orders is a readable Delta table."""
    table = read_delta("bronze", "orders/orders")
    assert table.num_rows > 0


def test_catalog_xlsx_produces_readable_bronze() -> None:
    """After materializing catalog_xlsx_assets, bronze/catalog/catalog is a readable Delta table."""
    table = read_delta("bronze", "catalog/catalog")
    assert table.num_rows > 0


def test_channel_api_produces_readable_bronze() -> None:
    """After materializing channel_api_assets, the nested Bronze table is readable."""
    table = read_delta("bronze", "channel_history/channel_history")
    assert table.num_rows > 0


def test_erp_db_produces_readable_bronze() -> None:
    """After materializing erp_db_assets, bronze/customers/customers is a readable Delta table."""
    table = read_delta("bronze", "customers/customers")
    assert table.num_rows > 0
