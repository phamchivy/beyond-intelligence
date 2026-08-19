"""Bronze/Silver -> Silver/Gold, shared by every tabular dataset.

Adding a fourth or fifth tabular source is a `.sql` file and a contract,
because this single function is what every one of them runs.
"""

import time
from dataclasses import dataclass

from dagster import AssetExecutionContext, MaterializeResult, asset

from contracts.catalog import CONTRACT_VERSION as CATALOG_VERSION
from contracts.catalog import CatalogSchema
from contracts.channel_history import CONTRACT_VERSION as CHANNEL_VERSION
from contracts.channel_history import ChannelHistorySchema
from contracts.customers import CONTRACT_VERSION as CUSTOMERS_VERSION
from contracts.customers import CustomersSchema
from contracts.orders import CONTRACT_VERSION as ORDERS_VERSION
from contracts.orders import OrdersSchema
from defs.ingest import catalog_xlsx_assets, channel_api_assets, erp_db_assets, orders_csv_assets
from lib import db
from lib.contracts import split_on_contract
from lib.delta import write_delta
from lib.logging import get_logger, log_event
from lib.sql import duckdb_arrow, read_sql

logger = get_logger(__name__)


@dataclass
class RunStats:
    """Row counts and Delta commit info for one transform run."""

    rows_in: int
    rows_out: int
    rows_rejected: int
    delta_version: int
    duration_ms: int

    def as_metadata(self) -> dict:
        """Convert to a Dagster asset metadata dict."""
        return {
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "rows_rejected": self.rows_rejected,
            "delta_version": self.delta_version,
            "duration_ms": self.duration_ms,
        }


def transform_to_silver(
    entity: str, *, sql_name: str, contract, contract_version: str, run_id: str
) -> RunStats:
    """Run one Silver `.sql` file over Bronze, split on its contract, quarantine failures.

    Args:
        entity: The dataset name, e.g. ``"orders"``. Used for the Silver
            and quarantine table paths.
        sql_name: The `.sql` file under ``sql/transforms/silver/``.
        contract: The Pandera ``DataFrameModel`` to validate against.
        contract_version: The contract's version string, recorded on every
            quarantined row.
        run_id: The caller-generated run id (decision 8.13).

    Returns:
        Row counts and the Delta commit version this run produced.
    """
    start = time.perf_counter()
    sql = read_sql(f"silver/{sql_name}")
    table = duckdb_arrow(sql)
    good, bad = split_on_contract(table, contract)

    if bad.num_rows:
        write_delta("quarantine", entity, bad, mode="append")
        db.record_violation(
            run_id=run_id,
            dataset=entity,
            contract_version=contract_version,
            check_name="schema_validation",
            violation_code="CONTRACT_VIOLATION",
            failure_count=bad.num_rows,
            quarantine_table=f"quarantine/{entity}",
        )

    version = write_delta("silver", entity, good, mode="overwrite")
    duration_ms = int((time.perf_counter() - start) * 1000)
    log_event(
        logger, "info", "silver_transformed",
        run_id=run_id, dataset=entity, rows_in=table.num_rows,
        rows_out=good.num_rows, rows_rejected=bad.num_rows, duration_ms=duration_ms,
    )
    return RunStats(table.num_rows, good.num_rows, bad.num_rows, version, duration_ms)


def transform_to_gold(model: str, *, sql_name: str, run_id: str) -> RunStats:
    """Run one Gold `.sql` file over Silver. No contract split -- Gold trusts Silver.

    Args:
        model: The Gold model name, e.g. ``"fct_order"``.
        sql_name: The `.sql` file under ``sql/transforms/gold/``.
        run_id: The caller-generated run id.

    Returns:
        Row counts and the Delta commit version this run produced.
    """
    start = time.perf_counter()
    sql = read_sql(f"gold/{sql_name}")
    table = duckdb_arrow(sql)
    version = write_delta("gold", model, table, mode="overwrite")
    duration_ms = int((time.perf_counter() - start) * 1000)
    log_event(logger, "info", "gold_transformed", run_id=run_id, dataset=model,
              rows_out=table.num_rows, duration_ms=duration_ms)
    return RunStats(table.num_rows, table.num_rows, 0, version, duration_ms)


# ============================================================ Silver assets


@asset(key=["silver", "orders"], deps=[orders_csv_assets])
def silver_orders(context: AssetExecutionContext) -> MaterializeResult:
    """Silver `orders`, from the CSV source."""
    stats = transform_to_silver(
        "orders", sql_name="stg_erp__orders.sql", contract=OrdersSchema,
        contract_version=ORDERS_VERSION, run_id=context.run.run_id,
    )
    return MaterializeResult(metadata=stats.as_metadata())


@asset(key=["silver", "customers"], deps=[erp_db_assets])
def silver_customers(context: AssetExecutionContext) -> MaterializeResult:
    """Silver `customers`, from the Database source."""
    stats = transform_to_silver(
        "customers", sql_name="stg_erp__customers.sql", contract=CustomersSchema,
        contract_version=CUSTOMERS_VERSION, run_id=context.run.run_id,
    )
    return MaterializeResult(metadata=stats.as_metadata())


@asset(key=["silver", "catalog"], deps=[catalog_xlsx_assets])
def silver_catalog(context: AssetExecutionContext) -> MaterializeResult:
    """Silver `catalog`, from the Excel source."""
    stats = transform_to_silver(
        "catalog", sql_name="stg_shop__catalog.sql", contract=CatalogSchema,
        contract_version=CATALOG_VERSION, run_id=context.run.run_id,
    )
    return MaterializeResult(metadata=stats.as_metadata())


@asset(key=["silver", "channel_history"], deps=[channel_api_assets])
def silver_channel_history(context: AssetExecutionContext) -> MaterializeResult:
    """Silver `channel_history`, from the REST API source."""
    stats = transform_to_silver(
        "channel_history", sql_name="stg_api__channel_history.sql", contract=ChannelHistorySchema,
        contract_version=CHANNEL_VERSION, run_id=context.run.run_id,
    )
    return MaterializeResult(metadata=stats.as_metadata())


# ============================================================ Gold assets


@asset(key=["gold", "fct_order"], deps=[silver_orders, silver_customers])
def gold_fct_order(context: AssetExecutionContext) -> MaterializeResult:
    """Gold `fct_order`: orders joined to customers."""
    stats = transform_to_gold("fct_order", sql_name="fct_order.sql", run_id=context.run.run_id)
    return MaterializeResult(metadata=stats.as_metadata())


@asset(key=["gold", "dim_customer"], deps=[silver_customers, silver_orders])
def gold_dim_customer(context: AssetExecutionContext) -> MaterializeResult:
    """Gold `dim_customer`: customers with order aggregates."""
    stats = transform_to_gold(
        "dim_customer", sql_name="dim_customer.sql", run_id=context.run.run_id
    )
    return MaterializeResult(metadata=stats.as_metadata())


@asset(key=["gold", "dim_product"], deps=[silver_catalog])
def gold_dim_product(context: AssetExecutionContext) -> MaterializeResult:
    """Gold `dim_product`, from the Excel catalog source."""
    stats = transform_to_gold("dim_product", sql_name="dim_product.sql", run_id=context.run.run_id)
    return MaterializeResult(metadata=stats.as_metadata())


@asset(key=["gold", "fct_channel_metric"], deps=[silver_channel_history])
def gold_fct_channel_metric(context: AssetExecutionContext) -> MaterializeResult:
    """Gold `fct_channel_metric`, from the REST API channel-history source."""
    stats = transform_to_gold(
        "fct_channel_metric", sql_name="fct_channel_metric.sql", run_id=context.run.run_id
    )
    return MaterializeResult(metadata=stats.as_metadata())
