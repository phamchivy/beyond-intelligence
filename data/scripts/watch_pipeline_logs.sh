#!/bin/sh
# Tail the currently running kalodata-cron pipeline container's logs.
#
# The container name changes every run (`docker compose run` appends a
# random suffix), so this finds whichever one is live right now instead of
# needing the name typed in each time. Run from `data/`::
#
#     ./scripts/watch_pipeline_logs.sh          # follow live
#     ./scripts/watch_pipeline_logs.sh --tail   # dump what's there, don't follow

set -e

# Prefer a one-off `docker compose run` container (the one actually doing
# work) over the always-on scheduler service, which just idles in cron.
container=$(docker ps --filter "name=kalodata-cron-run" --format "{{.Names}}" | head -n 1)
if [ -z "$container" ]; then
    container=$(docker ps --filter "name=kalodata-cron" --format "{{.Names}}" | head -n 1)
fi

if [ -z "$container" ]; then
    echo "no kalodata-cron container is running" >&2
    exit 1
fi

if [ "$1" = "--tail" ]; then
    docker logs "$container"
else
    docker logs -f "$container"
fi
