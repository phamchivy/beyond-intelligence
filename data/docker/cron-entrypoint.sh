#!/bin/sh
# cron strips the container's environment by default -- persist it to a
# file the cron job sources, the standard docker+cron idiom. Without this,
# DATABASE_URL/KALODATA_API_KEY/etc. (set via docker-compose env_file /
# environment) would never reach the scheduled job.
set -e

# Any args passed (e.g. `docker compose run kalodata-cron python -m ...`
# without an --entrypoint override) run directly instead of starting the
# scheduler -- otherwise they'd silently be ignored and this would start
# cron -f regardless of what was asked for.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

printenv > /app/.cron.env
echo "0 3 * * * cd /app && . /app/.cron.env && python -m scripts.kalodata_daily_pipeline >> /proc/1/fd/1 2>&1" | crontab -
cron -f
