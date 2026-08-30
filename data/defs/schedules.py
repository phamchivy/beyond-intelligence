"""Dagster schedules for the reference-corpus pipelines.

Scheduled runs are for reference corpora -- catalogs, policy documents,
channel history -- as opposed to request-time runs triggered by an HTTP
call (architecture §1). This build has no request-time path (that is
media's `POST /api/v1/assets`, which is excluded), so this is the only
trigger.
"""

from dagster import AssetSelection, ScheduleDefinition, define_asset_job

# AssetSelection.all(), not the "*" string form -- the installed dagster's
# antlr4-based string-selection parser errors on this environment's
# antlr4-python3-runtime build. AssetSelection.all() is the same selection
# without going through that parser.
full_refresh_job = define_asset_job(name="full_refresh", selection=AssetSelection.all())

daily_full_refresh = ScheduleDefinition(
    job=full_refresh_job,
    cron_schedule="0 3 * * *",  # 03:00 UTC daily
)
