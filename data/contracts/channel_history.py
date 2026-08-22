"""Contract for the channel history dataset -- sourced from the REST API pipeline."""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series

CONTRACT_VERSION = "channel_history-v1"


class ChannelHistorySchema(pa.DataFrameModel):
    """Silver-layer contract for `channel_history`."""

    event_id: Series[str] = pa.Field(unique=True)
    channel: Series[str]
    metric: Series[str]
    value: Series[float] = pa.Field(ge=0.0)
    updated_at: Series[object]
