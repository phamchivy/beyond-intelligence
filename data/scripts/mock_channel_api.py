"""A tiny FastAPI stub standing in for a real channel-history REST API.

Serves real `paging.next` pagination and an `updated_since` filter so
dlt's `rest_api_source` paginator and incremental cursor (defs/ingest.py)
are genuinely exercised. Run with:
`uvicorn scripts.mock_channel_api:app --port 8099`.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI, Header

app = FastAPI(title="Mock channel-history API")

random.seed(11)
_METRICS = ["views", "clicks", "conversions", "spend"]
_CHANNELS = ["tiktok_shop", "shopee", "lazada"]
_PAGE_SIZE = 20

_EVENTS = [
    {
        "event_id": f"EVT-{i:05d}",
        "channel": random.choice(_CHANNELS),
        "metric": random.choice(_METRICS),
        "value": round(random.uniform(1, 10_000), 2),
        "updated_at": (datetime(2026, 8, 1, tzinfo=UTC) + timedelta(hours=i)).isoformat(),
    }
    for i in range(80)
]


@app.get("/v1/channel/history")
def channel_history(
    page: int = 1,
    updated_since: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Return one page of channel-history events, filtered by `updated_since`."""
    events = _EVENTS
    if updated_since:
        events = [e for e in events if e["updated_at"] > updated_since]

    start = (page - 1) * _PAGE_SIZE
    end = start + _PAGE_SIZE
    page_events = events[start:end]
    has_next = end < len(events)

    return {
        "data": page_events,
        "paging": {"next": f"/v1/channel/history?page={page + 1}" if has_next else None},
    }
