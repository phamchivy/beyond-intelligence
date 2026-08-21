"""
Settings -- nguon cau hinh DUY NHAT cho `data/service/`.

Tat ca gia tri o day co the override qua bien moi truong / file .env
o thu muc goc `data/`. Import `settings` da khoi tao san, KHONG tu goi
`Settings()` o noi khac.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # S3 -- no local MinIO. s3_endpoint=None -> boto3 resolves the real
    # AWS endpoint for s3_region. Only set it if pointing at a
    # self-hosted S3-compatible store.
    s3_endpoint: str | None = None
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "ap-southeast-1"
    s3_addressing_style: str = "auto"
    bucket_raw: str = "raw-assets"
    bucket_processed: str = "processed-assets"
    # When set: everything goes into this ONE real bucket, with
    # bucket_raw/processed used as key prefixes instead of real bucket
    # names. Real AWS creds here are near-always scoped to one bucket
    # (no CreateBucket permission) -- see storage.ensure_buckets().
    s3_bucket: str | None = None

    # Auth
    internal_token: str = "dev-only-token-change-me"

    # Size / safety caps
    max_asset_bytes: int = 26_214_400  # 25 MB
    max_image_pixels: int = 50_000_000

    # Imaging
    target_long_edge: int = 4096
    jpeg_quality: int = 90

    # Cutout (background removal) -- see imaging.py
    cutout_backend: str = "rembg"  # rembg | replicate | none
    cutout_model: str = "u2netp"
    cutout_roles_raw: str = Field(default="hero,closeup,variant", alias="cutout_roles")
    cutout_concurrency: int = 2
    cutout_timeout: float = 20.0
    replicate_api_token: str | None = None

    # Misc TTLs
    presign_ttl_seconds: int = 3600

    @property
    def cutout_roles(self) -> list[str]:
        return [r.strip() for r in self.cutout_roles_raw.split(",") if r.strip()]

    @field_validator("cutout_backend")
    @classmethod
    def _valid_backend(cls, v: str) -> str:
        if v not in {"rembg", "replicate", "none"}:
            raise ValueError("CUTOUT_BACKEND phai la rembg | replicate | none")
        return v


settings = Settings()
