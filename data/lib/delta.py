"""Read and write Delta tables. The one write path for every layer.

DuckDB never writes Delta -- it reads, computes, and hands back Arrow
(lib.sql); ``deltalake`` (delta-rs) performs every write, here. That keeps
atomicity and schema enforcement uniform across all six pipelines.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from lib.settings import settings

_LAYER_URLS = {
    "landing": lambda: settings.storage.landing_url,
    "bronze": lambda: settings.storage.bronze_url,
    "silver": lambda: settings.storage.silver_url,
    "gold": lambda: settings.storage.gold_url,
    "quarantine": lambda: settings.storage.quarantine_url,
}


def storage_options() -> dict[str, str]:
    """Return the credential dict delta-rs needs on every call.

    Returns:
        The dict from ``Settings.storage.storage_options``, built once
        here so no call site assembles it by hand.
    """
    return settings.storage.storage_options


def s3_filesystem():
    """Build an s3fs filesystem handle against the configured storage.

    Imported lazily -- s3fs pulls in aiobotocore, whose pinned botocore
    range can drift from the one another dependency in this venv needs.
    Importing it only when a real blob read/write is about to happen
    keeps that fragility from blocking module import in unit tests, which
    fake this out and never call it.

    Returns:
        An ``s3fs.S3FileSystem`` pointed at ``settings.storage``.
    """
    import s3fs

    client_kwargs = {"region_name": settings.storage.region}
    if settings.storage.is_local:
        client_kwargs["endpoint_url"] = settings.storage.endpoint_url

    return s3fs.S3FileSystem(
        key=settings.storage.access_key,
        secret=settings.storage.secret_key,
        client_kwargs=client_kwargs,
        config_kwargs={"s3": {"addressing_style": settings.storage.addressing_style}},
    )


def table_uri(layer: str, name: str) -> str:
    """Build a Delta table URI from its layer and name, never string concatenation.

    Args:
        layer: One of ``landing``, ``bronze``, ``silver``, ``gold``, ``quarantine``.
        name: The dataset or entity name, e.g. ``"orders"``.

    Returns:
        The full URI, e.g. ``s3://bi-data-dev/silver/orders``.

    Raises:
        KeyError: If ``layer`` is not one of the five recognised layers.
    """
    return f"{_LAYER_URLS[layer]()}/{name}"


def read_delta(layer: str, name: str, *, version: int | None = None) -> pa.Table:
    """Read a Delta table as an Arrow table.

    Args:
        layer: One of ``landing``, ``bronze``, ``silver``, ``gold``, ``quarantine``.
        name: The dataset or entity name.
        version: An optional Delta version to time-travel to.

    Returns:
        The table's contents as a PyArrow table.
    """
    dt = DeltaTable(table_uri(layer, name), storage_options=storage_options(), version=version)
    return dt.to_pyarrow_table()


def write_delta(
    layer: str,
    name: str,
    table: pa.Table,
    *,
    mode: str = "overwrite",
    partition_by: list[str] | None = None,
    schema_mode: str | None = None,
) -> int:
    """Write an Arrow table to Delta as one atomic commit.

    Args:
        layer: One of ``landing``, ``bronze``, ``silver``, ``gold``, ``quarantine``.
        name: The dataset or entity name.
        table: The Arrow table to write.
        mode: ``"overwrite"`` or ``"append"``. Silver and Gold overwrite;
            Landing, Bronze and quarantine append.
        partition_by: Optional partition columns. Delta records
            partitioning in its own metadata -- there is no Hive-style
            path convention to construct here.
        schema_mode: ``None`` (strict, the default) or ``"merge"``.
            ``"merge"`` is opt-in per write for a deliberate additive
            change (decision 8.19) -- never pass it to silence a failing
            write. A write failing on a schema mismatch is the contract
            working.

    Returns:
        The Delta commit version this write produced, so callers can
        record it in ``ops.run_log.delta_version`` without a second call.
    """
    uri = table_uri(layer, name)
    write_deltalake(
        uri,
        table,
        mode=mode,
        partition_by=partition_by,
        schema_mode=schema_mode,
        storage_options=storage_options(),
    )
    return table_version(layer, name) or 0


def table_version(layer: str, name: str) -> int | None:
    """Return a Delta table's current commit version, or None if it doesn't exist yet.

    Args:
        layer: One of ``landing``, ``bronze``, ``silver``, ``gold``, ``quarantine``.
        name: The dataset or entity name.

    Returns:
        The current version number, or ``None`` if the table has not been
        written yet.
    """
    try:
        return DeltaTable(table_uri(layer, name), storage_options=storage_options()).version()
    except Exception:
        return None


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Compute the SHA-256 hex digest of a file, streamed.

    Args:
        path: Path to the file on local disk.
        chunk_size: Bytes read per iteration. Must stream -- a large blob
            (e.g. a document upload) is never held in memory to hash it.

    Returns:
        The lowercase hex digest.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
