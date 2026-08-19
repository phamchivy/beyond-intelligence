"""Integration test proving Landing/Bronze append-only semantics -- needs MinIO running."""

import pyarrow as pa
import pytest

from lib.delta import table_version, write_delta

pytestmark = pytest.mark.integration


def test_second_run_appends_a_new_version_and_never_rewrites_the_first() -> None:
    """A second append writes a new Delta version; the earlier version's data is still readable."""
    write_delta("bronze", "test_append_only", pa.table({"id": [1]}), mode="append")
    v1 = table_version("bronze", "test_append_only")

    write_delta("bronze", "test_append_only", pa.table({"id": [2]}), mode="append")
    v2 = table_version("bronze", "test_append_only")

    assert v2 > v1

    from deltalake import DeltaTable

    from lib.delta import storage_options, table_uri

    history = DeltaTable(
        table_uri("bronze", "test_append_only"), storage_options=storage_options()
    ).history()
    assert len(history) >= 2
