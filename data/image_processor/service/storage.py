"""
S3/MinIO wrapper -- one boto3 client for the whole service, plus the two
key-validation helpers that carry the trust-boundary checks (see §15 of
the blueprint). Every route that resolves a caller-supplied key MUST go
through split_ref() or validate_raw_key() before touching S3.
"""
from __future__ import annotations

from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from service.config import settings

_KNOWN_BUCKETS = {
    settings.bucket_raw: settings.bucket_raw,
    settings.bucket_processed: settings.bucket_processed,
}


class InvalidKey(Exception):
    pass


class ObjectNotFound(Exception):
    pass


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=BotoConfig(s3={"addressing_style": settings.s3_addressing_style}),
    )


def _physical(bucket: str, key: str) -> tuple[str, str]:
    """
    Translate a logical (bucket, key) to what actually goes over the
    wire. In multi-bucket/MinIO mode this is a no-op. When s3_bucket is
    set (a single real S3 bucket, typically all an IAM key is scoped
    to) every logical bucket becomes a key prefix inside that one
    bucket instead -- e.g. raw-assets/{task}/{asset}.jpg.
    """
    if settings.s3_bucket:
        return settings.s3_bucket, f"{bucket}/{key}"
    return bucket, key


def split_ref(ref: str, *, default_bucket: str | None = None) -> tuple[str, str]:
    """
    Parse "bucket/key" or a bare key (against default_bucket) into
    (bucket, key). Rejects traversal and unknown buckets -- this is the
    only place callers are allowed to turn a string into an S3 address.
    """
    ref = ref.strip().lstrip("/")
    if not ref or ".." in ref.split("/"):
        raise InvalidKey(f"key khong hop le: {ref!r}")

    parts = ref.split("/", 1)
    if len(parts) == 2 and parts[0] in _KNOWN_BUCKETS:
        bucket, key = parts[0], parts[1]
    elif default_bucket is not None:
        bucket, key = default_bucket, ref
    else:
        raise InvalidKey(f"khong xac dinh duoc bucket cho key: {ref!r}")

    if bucket not in _KNOWN_BUCKETS:
        raise InvalidKey(f"bucket khong hop le: {bucket!r}")
    if not key or ".." in key.split("/"):
        raise InvalidKey(f"key khong hop le: {key!r}")
    return bucket, key


def validate_raw_key(object_key: str, task_id: str) -> str:
    """
    Extra check for keys arriving from Backend at /data/assets/process:
    the key must live under raw-assets AND under this task's own prefix.
    Without this a caller naming an arbitrary key reads other tenants'
    raw uploads.
    """
    bucket, key = split_ref(object_key, default_bucket=settings.bucket_raw)
    if bucket != settings.bucket_raw:
        raise InvalidKey(f"raw asset phai nam trong bucket {settings.bucket_raw}")
    if not key.startswith(f"{task_id}/"):
        raise InvalidKey(f"key {key!r} khong thuoc task {task_id!r}")
    return key


def ensure_buckets() -> None:
    """
    MinIO/dev mode: create the three buckets if missing. Single-bucket
    mode is skipped entirely -- a real AWS key scoped to one bucket
    almost never has CreateBucket, and there's nothing to create
    anyway (the bucket already exists; logical buckets are prefixes).
    """
    if settings.s3_bucket:
        return
    c = _client()
    existing = {b["Name"] for b in c.list_buckets().get("Buckets", [])}
    for name in _KNOWN_BUCKETS:
        if name not in existing:
            c.create_bucket(Bucket=name)


def head(bucket: str, key: str) -> dict:
    pb, pk = _physical(bucket, key)
    try:
        return _client().head_object(Bucket=pb, Key=pk)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            raise ObjectNotFound(f"{bucket}/{key}") from e
        raise


def get_bytes(bucket: str, key: str) -> bytes:
    pb, pk = _physical(bucket, key)
    try:
        return _client().get_object(Bucket=pb, Key=pk)["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            raise ObjectNotFound(f"{bucket}/{key}") from e
        raise


def put_bytes(bucket: str, key: str, data: bytes, content_type: str) -> None:
    pb, pk = _physical(bucket, key)
    _client().put_object(Bucket=pb, Key=pk, Body=data, ContentType=content_type)


def presign(bucket: str, key: str, ttl: int | None = None) -> str:
    pb, pk = _physical(bucket, key)
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": pb, "Key": pk},
        ExpiresIn=ttl or settings.presign_ttl_seconds,
    )
