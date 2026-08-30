"""Quality gates, expressed where the asset is.

Whether a failure blocks downstream work is a Dagster decision. Thresholds
live in Settings, never in code -- a hard-coded `if bad > 100` breaks the
first week real volume passes it, and it breaks by blocking a healthy
pipeline.
"""

from dagster import AssetCheckResult, asset_check

from defs.evaluate import eval_retrieval
from defs.transform import silver_catalog, silver_channel_history, silver_customers, silver_orders
from lib.settings import settings


def _rejected_ratio_check(asset_def):
    """Build an @asset_check that fails when the rejected row ratio exceeds the configured max."""
    check_name = f"{asset_def.key.path[-1]}_rejected_ratio"

    @asset_check(asset=asset_def, blocking=settings.quality.blocking, name=check_name)
    def check(context) -> AssetCheckResult:
        materialization = context.instance.get_latest_materialization_event(asset_def.key)
        if materialization is None or materialization.asset_materialization is None:
            return AssetCheckResult(passed=True, metadata={"reason": "no materialization yet"})
        metadata = materialization.asset_materialization.metadata
        rows_out = metadata.get("rows_out")
        rows_rejected = metadata.get("rows_rejected")
        rows_out_v = rows_out.value if rows_out else 0
        rows_rejected_v = rows_rejected.value if rows_rejected else 0
        total = rows_out_v + rows_rejected_v
        ratio = (rows_rejected_v / total) if total else 0.0
        return AssetCheckResult(
            passed=ratio <= settings.quality.max_rejected_ratio,
            metadata={"rejected_ratio": ratio, "rows_rejected": rows_rejected_v},
        )

    return check


orders_rejected_ratio = _rejected_ratio_check(silver_orders)
customers_rejected_ratio = _rejected_ratio_check(silver_customers)
catalog_rejected_ratio = _rejected_ratio_check(silver_catalog)
channel_history_rejected_ratio = _rejected_ratio_check(silver_channel_history)


@asset_check(asset=eval_retrieval, blocking=False)
def hybrid_meets_quality_bar(context) -> AssetCheckResult:
    """Non-blocking: a retrieval quality regression should be loud, not a build break."""
    materialization = context.instance.get_latest_materialization_event(eval_retrieval.key)
    if materialization is None or materialization.asset_materialization is None:
        return AssetCheckResult(passed=True, metadata={"reason": "no materialization yet"})
    f1 = materialization.asset_materialization.metadata.get("hybrid_rrf_f1")
    f1_v = f1.value if f1 else 0.0
    return AssetCheckResult(passed=f1_v >= settings.eval.min_f1, metadata={"hybrid_f1": f1_v})
