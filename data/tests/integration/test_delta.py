"""Integration tests for lib.delta -- needs object storage reachable per STORAGE_* settings."""

import hashlib
import tempfile

import pyarrow as pa
import pytest

from lib.delta import read_delta, sha256_file, table_version, write_delta

pytestmark = pytest.mark.integration


def test_write_read_roundtrip_and_history() -> None:
    """Write, read back, and confirm history() shows two versions after a second write."""
    table = pa.table({"id": [1, 2, 3]})
    write_delta("silver", "test_delta_roundtrip", table, mode="overwrite")
    v1 = table_version("silver", "test_delta_roundtrip")

    write_delta("silver", "test_delta_roundtrip", table, mode="overwrite")
    v2 = table_version("silver", "test_delta_roundtrip")

    assert v2 > v1
    read_back = read_delta("silver", "test_delta_roundtrip")
    assert read_back.num_rows == 3


def test_sha256_of_large_file_matches_hashlib() -> None:
    """Streamed sha256_file matches a direct hashlib digest of a 10 MB file."""
    with tempfile.NamedTemporaryFile() as f:
        data = b"x" * (10 * 1024 * 1024)
        f.write(data)
        f.flush()
        assert sha256_file(f.name) == hashlib.sha256(data).hexdigest()
