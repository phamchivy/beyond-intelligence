"""The four tabular dlt sources, as Dagster assets writing Landing + Bronze Delta.

Every tabular source shares the same shape: dlt reads the external source,
copies the untouched bytes to Landing, and writes a schema-inferred Bronze
Delta table. From Silver onward all four run the identical
``transform_to_silver`` function against their own `.sql` file (defs/transform.py)
-- adding a source here costs a source definition and a `.sql` file, not a
new pipeline.
"""

from pathlib import Path

import dlt
import polars as pl
import s3fs
from dagster import AssetExecutionContext, MaterializeResult, asset
from dagster_dlt import DagsterDltResource, dlt_assets
from dlt.sources.filesystem import filesystem, read_csv
from dlt.sources.rest_api import rest_api_source
from dlt.sources.sql_database import sql_database

from lib.logging import get_logger, log_event
from lib.settings import settings

logger = get_logger(__name__)

_SEEDS_ROOT = Path(__file__).resolve().parent.parent / "seeds"


def _copy_to_landing(local_dir: Path, prefix: str) -> int:
    """Upload every file in ``local_dir`` to Landing, byte-for-byte, unparsed.

    Args:
        local_dir: Directory of source files on local disk.
        prefix: Sub-path under Landing to write them to, e.g. ``"csv"``.

    Returns:
        The number of files copied.
    """
    fs = s3fs.S3FileSystem(
        key=settings.storage.access_key,
        secret=settings.storage.secret_key,
        client_kwargs={"endpoint_url": settings.storage.endpoint_url},
    )
    dest_root = f"{settings.storage.landing_url.replace('s3://', '')}/{prefix}"
    count = 0
    for path in sorted(local_dir.glob("*")):
        if path.is_file():
            fs.put(str(path), f"{dest_root}/{path.name}")
            count += 1
    return count


# ============================================================ 1. CSV — orders


@dlt.source(name="orders_csv")
def orders_csv_source(bucket_url: str = str(_SEEDS_ROOT / "csv")):
    """Dlt source reading every ``orders*.csv`` file under the seed directory."""
    # .with_name pins the table name to "orders" -- dlt otherwise names the
    # table after the read_csv transformer, and sql/transforms/silver/*.sql
    # reads bronze/orders/orders, not bronze/orders/read_csv.
    return (filesystem(bucket_url=bucket_url, file_glob="orders*.csv") | read_csv()).with_name(
        "orders"
    )


@dlt_assets(
    dlt_source=orders_csv_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="orders_csv",
        dataset_name="orders",
        destination=dlt.destinations.filesystem(
            settings.storage.bronze_url, credentials=settings.storage.dlt_credentials
        ),
    ),
)
def orders_csv_assets(context: AssetExecutionContext, dlt_resource: DagsterDltResource):
    """Landing + Bronze for the CSV orders source."""
    n = _copy_to_landing(_SEEDS_ROOT / "csv", "csv")
    log_event(logger, "info", "landing_copied", dataset="orders", file_count=n)
    yield from dlt_resource.run(context=context, table_format="delta")


# ============================================================ 2. Excel — catalog


@dlt.transformer(standalone=True)
def read_excel(items, sheet_name: str = "Sheet1"):
    """Read each Excel file item with Polars (calamine engine via fastexcel).

    dlt ships no Excel reader (tech-stack-evaluation.md §4) -- this is the
    one source type that needs code, and it costs about fifteen lines.
    """
    for item in items:
        with item.open() as f:
            # fastexcel needs a path or bytes, not a file-like object.
            yield pl.read_excel(f.read(), sheet_name=sheet_name, engine="calamine").to_dicts()


@dlt.source(name="catalog_xlsx")
def catalog_xlsx_source(bucket_url: str = str(_SEEDS_ROOT / "xlsx")):
    """Dlt source reading every ``*.xlsx`` file under the seed directory."""
    return (filesystem(bucket_url=bucket_url, file_glob="*.xlsx") | read_excel()).with_name(
        "catalog"
    )


@dlt_assets(
    dlt_source=catalog_xlsx_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="catalog_xlsx",
        dataset_name="catalog",
        destination=dlt.destinations.filesystem(
            settings.storage.bronze_url, credentials=settings.storage.dlt_credentials
        ),
    ),
)
def catalog_xlsx_assets(context: AssetExecutionContext, dlt_resource: DagsterDltResource):
    """Landing + Bronze for the Excel catalog source."""
    n = _copy_to_landing(_SEEDS_ROOT / "xlsx", "xlsx")
    log_event(logger, "info", "landing_copied", dataset="catalog", file_count=n)
    yield from dlt_resource.run(context=context, table_format="delta")


# ============================================================ 3. REST API — channel_history


def channel_api_source():
    """Dlt REST API source against the mock channel-history stub.

    Pagination, auth and the incremental cursor are configuration, not
    code -- dlt stores the cursor state, so a second run fetches only what
    changed since the last one.
    """
    return rest_api_source({
        "client": {
            "base_url": settings.sources.api_base_url,
            "auth": {"type": "bearer", "token": settings.sources.api_token.get_secret_value()},
            "paginator": {"type": "json_link", "next_url_path": "paging.next"},
        },
        "resources": [{
            "name": "channel_history",
            "endpoint": {
                "path": "/v1/channel/history",
                "data_selector": "data",
                "params": {"updated_since": {"type": "incremental", "cursor_path": "updated_at"}},
            },
        }],
    })


@dlt_assets(
    dlt_source=channel_api_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="channel_api",
        dataset_name="channel_history",
        destination=dlt.destinations.filesystem(
            settings.storage.bronze_url, credentials=settings.storage.dlt_credentials
        ),
    ),
)
def channel_api_assets(context: AssetExecutionContext, dlt_resource: DagsterDltResource):
    """Bronze for the REST API channel-history source.

    No Landing copy here -- the API response *is* the record, there is no
    separate "raw file" to preserve the way there is for CSV/Excel bytes.
    """
    yield from dlt_resource.run(context=context, table_format="delta")


# ============================================================ 4. Database — customers


def erp_db_source():
    """Dlt SQL database source reading the seeded ``source.customers`` table.

    ``backend="pyarrow"`` keeps source types stable through the write
    rather than letting Python objects decide them.
    """
    return sql_database(
        credentials=settings.sources.erp_dsn,
        schema="source",
        table_names=["customers"],
        backend="pyarrow",
    )


@asset(key=["bronze", "customers"])
def erp_db_assets(context: AssetExecutionContext) -> MaterializeResult:
    """Bronze for the Database customers source.

    Deliberately a plain ``@asset``, not ``@dlt_assets`` -- ``sql_database()``
    connects immediately to reflect table schemas, which the other three
    sources (filesystem, REST API) do not do at construction time. Building
    ``erp_db_source()`` at module import time would mean a live Postgres is
    required just to import ``defs``, breaking the "no container" rule for
    unit tests. This is the exact fallback stage 0.5's check 4 names: call
    the dlt pipeline inside a plain ``@asset`` -- a normal Python call, so
    the source is only constructed when this asset actually runs. No
    Landing copy -- there are no bytes here, only rows.
    """
    pipeline = dlt.pipeline(
        pipeline_name="erp_db",
        dataset_name="customers",
        destination=dlt.destinations.filesystem(
            settings.storage.bronze_url, credentials=settings.storage.dlt_credentials
        ),
    )
    load_info = pipeline.run(erp_db_source(), table_format="delta")
    log_event(logger, "info", "bronze_loaded", dataset="customers", load_info=str(load_info))
    return MaterializeResult(metadata={"pipeline": "erp_db"})
