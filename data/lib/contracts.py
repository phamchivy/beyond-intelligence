"""Split an Arrow table into valid and rejected rows against a Pandera contract.

One function, used by every pipeline. No ``Validator`` port, no
``ValidationResult`` entity, no second contract language in YAML.
"""

from __future__ import annotations

import polars as pl
import pyarrow as pa
from pandera.errors import SchemaErrors
from pandera.polars import DataFrameModel


def split_on_contract(table: pa.Table, schema: type[DataFrameModel]) -> tuple[pa.Table, pa.Table]:
    """Validate an Arrow table against a Pandera contract and split it.

    Uses ``pandera.polars`` with ``lazy=True`` (decision 8.14) so every
    violation is collected in one pass, not just the first. This function
    never raises on bad data -- that is the whole point: bad rows are
    quarantined, not dropped and not fatal to the run.

    Args:
        table: The Arrow table to validate.
        schema: A ``pandera.polars.DataFrameModel`` subclass.

    Returns:
        A tuple ``(valid, rejected)`` of Arrow tables. ``rejected`` is
        empty when every row passes.
    """
    df = pl.from_arrow(table)
    try:
        schema.validate(df, lazy=True)
        return table, table.slice(0, 0)
    except SchemaErrors as exc:
        bad_indices = set(exc.failure_cases["index"].drop_nulls().to_list())
        idx = df.with_row_index()
        valid = idx.filter(~pl.col("index").is_in(bad_indices)).drop("index")
        rejected = idx.filter(pl.col("index").is_in(bad_indices)).drop("index")
        return valid.to_arrow(), rejected.to_arrow()
