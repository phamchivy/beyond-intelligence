"""The single Definitions object `dagster dev` loads."""

import os

# Must be set before torch is imported (transitively, via docling below).
# Torch's default OpenMP thread pool oversubscribes alongside DuckDB's own
# thread pool and Dagster's step threads, which reliably deadlocks the
# document pipeline on multi-core machines -- confirmed by reproducing it
# standalone and watching every thread sit in `futex_do_wait` at 0% CPU.
# One BLAS/OpenMP thread per process is the right ceiling for a
# single-document-at-a-time pipeline; parallelism belongs to Dagster's
# executor, not to the model runtime underneath one step.
os.environ.setdefault("OMP_NUM_THREADS", "1")

from dagster import Definitions

from defs.checks import (
    catalog_rejected_ratio,
    channel_history_rejected_ratio,
    customers_rejected_ratio,
    hybrid_meets_quality_bar,
    orders_rejected_ratio,
)
from defs.documents import silver_document_chunk
from defs.evaluate import eval_retrieval
from defs.ingest import catalog_xlsx_assets, channel_api_assets, erp_db_assets, orders_csv_assets
from defs.publish import publish_gold
from defs.resources import db_resource, dlt_resource, embedder_resource
from defs.schedules import daily_full_refresh
from defs.transform import (
    gold_dim_customer,
    gold_dim_product,
    gold_fct_channel_metric,
    gold_fct_order,
    silver_catalog,
    silver_channel_history,
    silver_customers,
    silver_orders,
)

defs = Definitions(
    assets=[
        orders_csv_assets,
        catalog_xlsx_assets,
        channel_api_assets,
        erp_db_assets,
        silver_orders,
        silver_customers,
        silver_catalog,
        silver_channel_history,
        gold_fct_order,
        gold_dim_customer,
        gold_dim_product,
        gold_fct_channel_metric,
        silver_document_chunk,
        publish_gold,
        eval_retrieval,
    ],
    asset_checks=[
        orders_rejected_ratio,
        customers_rejected_ratio,
        catalog_rejected_ratio,
        channel_history_rejected_ratio,
        hybrid_meets_quality_bar,
    ],
    schedules=[daily_full_refresh],
    resources={
        "dlt_resource": dlt_resource,
        "db_resource": db_resource,
        "embedder_resource": embedder_resource,
    },
)
