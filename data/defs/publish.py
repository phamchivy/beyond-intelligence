"""Gold Delta -> Postgres `gold` + `api.v1_*` views, one transaction.

Publishing is a separate step so a half-built mart is never visible to the
backend: Gold rebuilds in Delta, then one narrow write moves the finished
result into Postgres. Gold lives in two places on purpose -- Delta for
analytics and reprocessing, Postgres for serving -- and this step is one
direction only. Delta is the source of truth.
"""

import pyarrow as pa
from dagster import AssetExecutionContext, MaterializeResult, asset

from defs.transform import (
    gold_dim_customer,
    gold_dim_product,
    gold_fct_channel_metric,
    gold_fct_order,
)
from lib import db
from lib.delta import read_delta
from lib.logging import get_logger, log_event

logger = get_logger(__name__)

_ARROW_TO_SQL = {
    pa.string(): "text",
    pa.int64(): "bigint",
    pa.float64(): "double precision",
    pa.date32(): "date",
}


def _sql_type(arrow_type: pa.DataType) -> str:
    """Map an Arrow type to a Postgres column type, defaulting to text."""
    return _ARROW_TO_SQL.get(arrow_type, "text")


def publish_gold_table(model: str, *, view_name: str) -> int:
    """Copy one Gold Delta table into `gold.<model>`, inside one transaction.

    Args:
        model: The Gold Delta table name, e.g. ``"fct_order"``.
        view_name: The `api.v1_*` view name to expose it as.

    Returns:
        Number of rows published.
    """
    table = read_delta("gold", model)
    columns_sql = ", ".join(
        f'"{name}" {_sql_type(dtype)}'
        for name, dtype in zip(table.column_names, table.schema.types, strict=True)
    )
    col_names = ", ".join(f'"{n}"' for n in table.column_names)
    placeholders = ", ".join(["%s"] * len(table.column_names))

    with db.connection() as conn:
        conn.execute(f'CREATE TABLE IF NOT EXISTS gold."{model}" ({columns_sql})')
        conn.execute(f'TRUNCATE gold."{model}"')
        rows = table.to_pylist()
        if rows:
            conn.cursor().executemany(
                f'INSERT INTO gold."{model}" ({col_names}) VALUES ({placeholders})',
                [tuple(r.values()) for r in rows],
            )
        conn.execute(f'CREATE OR REPLACE VIEW api.{view_name} AS SELECT * FROM gold."{model}"')

    log_event(logger, "info", "gold_published", dataset=model, rows=table.num_rows)
    return table.num_rows


@asset(
    key=["publish", "gold"],
    deps=[gold_fct_order, gold_dim_customer, gold_dim_product, gold_fct_channel_metric],
)
def publish_gold(context: AssetExecutionContext) -> MaterializeResult:
    """Publish every Gold Delta table into Postgres `gold.*` and `api.v1_*` views."""
    counts = {
        "fct_order": publish_gold_table("fct_order", view_name="v1_order_daily"),
        "dim_customer": publish_gold_table(
            "dim_customer", view_name="v1_customer_overview"
        ),
        "dim_product": publish_gold_table("dim_product", view_name="v1_product_overview"),
        "fct_channel_metric": publish_gold_table(
            "fct_channel_metric", view_name="v1_channel_metric"
        ),
    }
    return MaterializeResult(metadata=counts)
