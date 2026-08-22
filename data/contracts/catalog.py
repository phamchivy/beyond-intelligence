"""Contract for the product catalog dataset -- sourced from the Excel pipeline."""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series

CONTRACT_VERSION = "catalog-v1"


class CatalogSchema(pa.DataFrameModel):
    """Silver-layer contract for `catalog`."""

    sku: Series[str] = pa.Field(unique=True)
    product_name: Series[str]
    price: Series[float] = pa.Field(ge=0.0)
    category: Series[str]
