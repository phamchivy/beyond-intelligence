"""Contract for the orders dataset -- shared by the CSV and Database source pipelines."""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series

CONTRACT_VERSION = "orders-v1"


class OrdersSchema(pa.DataFrameModel):
    """Silver-layer contract for `orders`."""

    order_id: Series[str] = pa.Field(str_matches=r"^ORD-\d+$", unique=True)
    customer_id: Series[str]
    amount: Series[float] = pa.Field(ge=0.0)
    event_date: Series[object]
    classification: Series[str] = pa.Field(isin=["public", "internal", "confidential", "pii"])
