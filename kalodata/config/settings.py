"""
Vi tri file nay: data/config/settings.py

Nguon cau hinh DUY NHAT cho toan bo `data/`. Cung pattern da dung cho
`agent/config/settings.py` (_BaseAppSettings ke thua chung, Secret/
Deployment/Application behavior tach 3 loai) -- day la 2 FILE PYTHON
DOC LAP (khong import chung), vi `data/` va `agent/` la 2 Docker image
rieng, khong share code Python giua container (dung nguyen tac da chot
trong docs/architecture/integration-architecture.md).
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class _BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    MOCK = "mock"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


def _strip_whitespace(value: object) -> object:
    """Cat khoang trang thua tu .env -- xem giai thich chi tiet trong agent/config/settings.py."""
    if isinstance(value, str):
        return value.strip()
    return value


class LLMSettings(_BaseAppSettings):
    """Cau hinh LLM dung de tong hop Insight Report tu du lieu Kalodata."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: LLMProvider = LLMProvider.GEMINI
    model: str = "gemini-3.6-flash"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    thinking_level: str = "low"

    gemini_api_key: SecretStr | None = Field(default=None)
    deepseek_api_key: SecretStr | None = Field(default=None)
    base_url: str | None = Field(default="https://ark.ap-southeast.bytepluses.com/api/v3")

    @field_validator("provider", "model", "base_url", mode="before")
    @classmethod
    def _strip_llm_fields(cls, v: object) -> object:
        return _strip_whitespace(v)

    def require_api_key(self) -> SecretStr:
        key_map: dict[LLMProvider, SecretStr | None] = {
            LLMProvider.GEMINI: self.gemini_api_key,
            LLMProvider.DEEPSEEK: self.deepseek_api_key,
        }
        key = key_map.get(self.provider)
        if key is None:
            raise ValueError(
                f"Thieu API key cho provider '{self.provider.value}'. "
                f"Hay set bien moi truong LLM_{self.provider.value.upper()}_API_KEY."
            )
        return key


class KalodataSettings(_BaseAppSettings):
    """
    Cau hinh goi API Kalodata -- doc boi infrastructure/kalodata/kalodata_client.py.

    # TODO(config): tai lieu API duoc cung cap KHONG neu ro ten header
    # xac thuc (Authorization: Bearer? X-API-Key? khac?) -- de mac dinh
    # "Authorization" + scheme "Bearer" (pho bien nhat), CAN XAC NHAN
    # lai voi tai lieu auth chi tiet cua Kalodata hoac lien he ho truoc
    # khi chay that.
    """

    model_config = SettingsConfigDict(env_prefix="KALODATA_")

    base_url: str = "https://www.kalodata.com/openapi/v1/tiktok"
    api_key: SecretStr | None = Field(default=None)
    auth_header_name: str = "Authorization"
    auth_header_prefix: str = "Bearer "  # noi vao truoc api_key, vd "Bearer <key>"
    timeout_seconds: float = Field(default=15.0, gt=0)
    default_region: str = "US"
    default_language: str = "en-US"
    default_currency: str = "USD"

    @field_validator("base_url", "auth_header_name", mode="before")
    @classmethod
    def _strip_kalodata_fields(cls, v: object) -> object:
        return _strip_whitespace(v)

    def require_api_key(self) -> SecretStr:
        if self.api_key is None:
            raise ValueError(
                "Thieu API key cho Kalodata. Hay set bien moi truong KALODATA_API_KEY."
            )
        return self.api_key


class RetryPolicySettings(_BaseAppSettings):
    model_config = SettingsConfigDict(env_prefix="RETRY_")

    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay_seconds: float = Field(default=1.0, gt=0)
    max_delay_seconds: float = Field(default=30.0, gt=0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)


class ObservabilitySettings(_BaseAppSettings):
    model_config = SettingsConfigDict(env_prefix="OBSERVABILITY_")

    log_level: LogLevel = LogLevel.INFO
    log_prompts: bool = False


class Settings(_BaseAppSettings):
    app_name: str = "beyond-intelligence-data"
    environment: Environment = Environment.DEVELOPMENT

    llm: LLMSettings = Field(default_factory=LLMSettings)
    kalodata: KalodataSettings = Field(default_factory=KalodataSettings)
    retry_policy: RetryPolicySettings = Field(default_factory=RetryPolicySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    max_insight_revisions: int = Field(default=3, ge=1, le=10)
    # Danh sach nhom du lieu Kalodata se duoc query DONG THOI moi lan
    # tong hop Insight -- phan cach dau phay. Mo rong bang cach them
    # gia tri vao day (vd: "video,product,category,creator"), KHONG
    # can sua code trong InsightService. Xem MarketDataDomain de biet
    # cac gia tri hop le.
    insight_domains: str = Field(default="video,product,category")
    # So luong ket qua ranking lay ve truoc khi loc -- ranking tra ve
    # nhieu field tong hop san, KHONG can goi detail cho toan bo, chi
    # goi detail cho top N sau khi da loc (xem top_n_for_detail).
    ranking_page_size: int = Field(default=20, ge=1, le=100)
    top_n_for_detail: int = Field(default=10, ge=1, le=50)

    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


settings = Settings()