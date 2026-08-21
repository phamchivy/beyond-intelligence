"""The single configuration object for the data layer.

Every threshold, path, model name and limit that would otherwise be
hard-coded lives here instead, read once from the environment. Never call
``Settings()`` anywhere except this module -- import the ``settings``
singleton below.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """Object storage location and credentials for every Delta layer.

    ``storage_options`` is what delta-rs needs on *every* read and write --
    it does not fall back to ambient environment variables the way fsspec
    does. Building it here once, instead of at each call site, is what
    keeps a missing credential from presenting as a confusing "table not
    found" against a bucket that plainly exists.
    """

    model_config = SettingsConfigDict(env_prefix="STORAGE_")

    url: str = "s3://bi-data-dev"
    endpoint_url: str = "http://localhost:9000"
    access_key: str = "minio"
    secret_key: str = "minio123"

    @property
    def landing_url(self) -> str:
        """URI for the Landing layer (raw bytes, never parsed)."""
        return f"{self.url}/landing"

    @property
    def bronze_url(self) -> str:
        """URI for the Bronze Delta layer (schema inferred by dlt)."""
        return f"{self.url}/bronze"

    @property
    def silver_url(self) -> str:
        """URI for the Silver Delta layer (typed, contract-enforced)."""
        return f"{self.url}/silver"

    @property
    def gold_url(self) -> str:
        """URI for the Gold Delta layer (published to Postgres)."""
        return f"{self.url}/gold"

    @property
    def quarantine_url(self) -> str:
        """URI for rejected rows, kept with their violation attached."""
        return f"{self.url}/quarantine"

    @property
    def storage_options(self) -> dict[str, str]:
        """The credential dict every delta-rs and DuckDB S3 call needs."""
        return {
            "AWS_ENDPOINT_URL": self.endpoint_url,
            "AWS_ACCESS_KEY_ID": self.access_key,
            "AWS_SECRET_ACCESS_KEY": self.secret_key,
            "AWS_ALLOW_HTTP": "true",
            "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
        }

    @property
    def dlt_credentials(self) -> dict[str, str]:
        """The credential dict shape dlt's filesystem destination expects.

        Different key names than ``storage_options`` -- dlt and delta-rs
        each define their own S3 credential shape.
        """
        return {
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "endpoint_url": self.endpoint_url,
        }


class DatabaseSettings(BaseSettings):
    """Postgres connection strings for the two roles this layer uses."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str = "postgresql://bi:bi@localhost:5432/bi"
    backend_reader_url: str = "postgresql://backend_reader:backend_reader@localhost:5432/bi"


class SourceSettings(BaseSettings):
    """Connection details for the four tabular source types."""

    model_config = SettingsConfigDict(env_prefix="SOURCE_")

    csv_bucket: str = "seeds/csv"
    xlsx_bucket: str = "seeds/xlsx"
    api_base_url: str = "http://localhost:8099"
    api_token: SecretStr = SecretStr("dev-token")
    erp_dsn: str = "postgresql://bi:bi@localhost:5432/bi"


class KalodataSettings(BaseSettings):
    """Kalodata Open API -- TikTok Shop analytics, endpoints in kalodata/kalodata-api.txt.

    ``env_file`` is declared here and not only on ``Settings`` because a
    nested settings class reads its own sources: without it the API key
    would have to be exported into the environment by hand before every
    run, while the rest of this file's defaults happen to mask the same
    gap by being correct for local development.
    """

    model_config = SettingsConfigDict(env_prefix="KALODATA_", env_file=".env", extra="ignore")

    api_key: SecretStr = SecretStr("")
    base_url: str = "https://www.kalodata.com/openapi/v1/tiktok"
    region: str = "US"
    language: str = "en-US"
    currency: str = "USD"


class ChunkSettings(BaseSettings):
    """Document chunking limits, used by the HybridChunker path."""

    model_config = SettingsConfigDict(env_prefix="CHUNK_")

    max_tokens: int = 512
    overlap: int = 64


class RetrievalSettings(BaseSettings):
    """The hybrid retrieval query's tunables -- architecture doc §10."""

    model_config = SettingsConfigDict(env_prefix="RETRIEVAL_")

    rrf_k: int = 60
    top_k: int = 5
    max_top_k: int = 50
    leg_k: int = 50
    trigram_threshold: float = 0.2
    embedder_model_id: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class QualitySettings(BaseSettings):
    """The threshold that decides whether a quality gate blocks downstream work."""

    model_config = SettingsConfigDict(env_prefix="QUALITY_")

    max_rejected_ratio: float = 0.05
    blocking: bool = True


class EvalSettings(BaseSettings):
    """Where the evaluation harness reads cases from and writes reports to."""

    model_config = SettingsConfigDict(env_prefix="EVAL_")

    dataset_path: str = "evaluation/datasets/retrieval.jsonl"
    report_dir: str = "evaluation/reports"
    min_f1: float = 0.5


class ApiSettings(BaseSettings):
    """Bind address for the FastAPI edge."""

    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = "0.0.0.0"
    port: int = 8002


class Settings(BaseSettings):
    """The layer's single configuration object, one nested class per concern."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    storage: StorageSettings = Field(default_factory=StorageSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    sources: SourceSettings = Field(default_factory=SourceSettings)
    kalodata: KalodataSettings = Field(default_factory=KalodataSettings)
    chunk: ChunkSettings = Field(default_factory=ChunkSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    quality: QualitySettings = Field(default_factory=QualitySettings)
    eval: EvalSettings = Field(default_factory=EvalSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)


settings = Settings()
