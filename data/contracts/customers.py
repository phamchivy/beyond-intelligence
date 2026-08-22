"""Contract for the customers dataset -- sourced from the ERP database pipeline."""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series

CONTRACT_VERSION = "customers-v1"


class CustomersSchema(pa.DataFrameModel):
    """Silver-layer contract for `customers`."""

    customer_id: Series[str] = pa.Field(unique=True)
    name: Series[str]
    country: Series[str] = pa.Field(str_length=(2, 2))
