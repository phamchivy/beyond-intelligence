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

    # env_file is declared on every nested class, not only on Settings --
    # a nested BaseSettings reads its own sources independently and does
    # not inherit the parent's env_file, so without this it silently sees
    # only real process environment variables and never .env. Every
    # nested class below repeats this for the same reason.
    model_config = SettingsConfigDict(env_prefix="STORAGE_", env_file=".env", extra="ignore")

    url: str = "s3://bi-data-dev"
    # Empty means "real AWS, let boto resolve it" -- only a local
    # S3-compatible emulator needs a fixed endpoint URL here.
    endpoint_url: str = ""
    access_key: str = ""
    secret_key: str = ""
    region: str = "us-east-1"
    addressing_style: str = "auto"

    @property
    def is_local(self) -> bool:
        """True when a custom endpoint is set (a local S3-compatible emulator).

        False for real AWS S3.
        """
        return bool(self.endpoint_url)

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
    def index_url(self) -> str:
        """URI for the retrieval index snapshot -- a Postgres backup, not a pipeline layer."""
        return f"{self.url}/index"

    @property
    def storage_options(self) -> dict[str, str]:
        """The credential dict every delta-rs and DuckDB S3 call needs.

        ``AWS_ALLOW_HTTP`` and ``AWS_S3_ALLOW_UNSAFE_RENAME`` are local
        S3-compatible emulator compatibility flags -- real S3 supports
        proper conditional PUTs and must not fall back to the unsafe
        rename path, so both are scoped to ``is_local`` rather than sent
        unconditionally.
        """
        options = {
            "AWS_REGION": self.region,
            "AWS_ACCESS_KEY_ID": self.access_key,
            "AWS_SECRET_ACCESS_KEY": self.secret_key,
        }
        if self.is_local:
            options |= {
                "AWS_ENDPOINT_URL": self.endpoint_url,
                "AWS_ALLOW_HTTP": "true",
                "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
            }
        return options

    @property
    def dlt_credentials(self) -> dict[str, str]:
        """The credential dict shape dlt's filesystem destination expects.

        Different key names than ``storage_options`` -- dlt and delta-rs
        each define their own S3 credential shape.
        """
        credentials = {
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "region_name": self.region,
        }
        if self.is_local:
            credentials["endpoint_url"] = self.endpoint_url
        return credentials


class DatabaseSettings(BaseSettings):
    """Postgres connection strings for the two roles this layer uses."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_", env_file=".env", extra="ignore")

    url: str = "postgresql://bi:bi@localhost:5432/bi"
    backend_reader_url: str = "postgresql://backend_reader:backend_reader@localhost:5432/bi"


class SourceSettings(BaseSettings):
    """Connection details for the four tabular source types."""

    model_config = SettingsConfigDict(env_prefix="SOURCE_", env_file=".env", extra="ignore")

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


class GeminiSettings(BaseSettings):
    """Gemini video understanding -- the only model that reads the .mp4 directly.

    ``prompt_version`` is part of the idempotency key the analyze script
    checks against Silver, not metadata: change the prompt or the model
    and old storyboards must not silently mix with new ones (architecture
    doc §6.6).
    """

    model_config = SettingsConfigDict(env_prefix="GEMINI_", env_file=".env", extra="ignore")

    api_key: SecretStr = SecretStr("")
    model: str = "gemini-3.6-flash"
    prompt_version: str = "storyboard-v1"


class ChunkSettings(BaseSettings):
    """Document chunking limits, used by the HybridChunker path."""

    model_config = SettingsConfigDict(env_prefix="CHUNK_", env_file=".env", extra="ignore")

    max_tokens: int = 512
    overlap: int = 64


class RetrievalSettings(BaseSettings):
    """The hybrid retrieval query's tunables -- architecture doc §10."""

    model_config = SettingsConfigDict(env_prefix="RETRIEVAL_", env_file=".env", extra="ignore")

    rrf_k: int = 60
    top_k: int = 5
    max_top_k: int = 50
    leg_k: int = 50
    trigram_threshold: float = 0.2
    embedder_model_id: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Reranking. RRF fuses ranks, so it knows a chunk placed well in both
    # legs but nothing about whether the text answers the query -- and an
    # RRF score has no absolute scale to threshold against. A cross-encoder
    # score does, which is what makes ``rerank_min_score`` meaningful.
    reranker_model_id: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    rerank_min_score: float = 0.0
    candidate_k: int = 50

    # Trending decay, not a cutoff: a hard "last N days" filter returns
    # nothing on a thin bucket.
    trending_half_life_days: float = 14.0


class QualitySettings(BaseSettings):
    """The threshold that decides whether a quality gate blocks downstream work."""

    model_config = SettingsConfigDict(env_prefix="QUALITY_", env_file=".env", extra="ignore")

    max_rejected_ratio: float = 0.05
    blocking: bool = True


class EvalSettings(BaseSettings):
    """Where the evaluation harness reads cases from and writes reports to."""

    model_config = SettingsConfigDict(env_prefix="EVAL_", env_file=".env", extra="ignore")

    dataset_path: str = "evaluation/datasets/retrieval.jsonl"
    report_dir: str = "evaluation/reports"
    min_f1: float = 0.5


class ApiSettings(BaseSettings):
    """Bind address for the FastAPI edge."""

    model_config = SettingsConfigDict(env_prefix="API_", env_file=".env", extra="ignore")

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
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    chunk: ChunkSettings = Field(default_factory=ChunkSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    quality: QualitySettings = Field(default_factory=QualitySettings)
    eval: EvalSettings = Field(default_factory=EvalSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)


settings = Settings()
