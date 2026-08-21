"""Pydantic request/response models for the Data pod HTTP API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AssetIn(BaseModel):
    asset_id: str
    object_key: str
    asset_role: str
    mime_type: str


class ProcessRequest(BaseModel):
    task_id: str
    assets: list[AssetIn]


class AssetMetadata(BaseModel):
    width: int
    height: int
    bytes: int
    source_format: str
    had_alpha: bool
    cutout: Literal["ok", "skipped", "failed"]


class AssetOut(BaseModel):
    asset_id: str
    asset_role: str
    mime_type: str
    object_presigned_url: str
    object_ref: str
    cutout_ref: str | None = None
    cutout_presigned_url: str | None = None
    metadata: AssetMetadata


class AssetFailure(BaseModel):
    asset_id: str
    reason: str


class ProcessResponse(BaseModel):
    assets: list[AssetOut]
    failed: list[AssetFailure]
