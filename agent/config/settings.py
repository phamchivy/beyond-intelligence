"""
Settings -- nguon cau hinh DUY NHAT cho toan bo `agent/`.

Nguyen tac (Twelve-Factor App + quy tac da thong nhat trong du an):

  1. Secret (API key, password, token)
     -> LUON lay tu bien moi truong / secret manager.
     -> KHONG BAO GIO hardcode hay commit vao file .env that.
     -> Dung SecretStr de tranh lo ra ngoai khi log()/print() nham.

  2. Deployment config (log level, provider, endpoint)
     -> Bien moi truong, khac nhau giua dev / staging / production.

  3. Application behavior (threshold, timeout, max_iterations...)
     -> Co gia tri mac dinh hop ly (typed), van co the override qua env
        khi can tinh chinh ma khong sua code.

TUYET DOI KHONG hardcode gia tri cau hinh o BAT KY noi nao khac trong
`agent/` (ten model, threshold, temperature, timeout, so lan retry...).
Moi noi can dung gia tri nay phai `from config.settings import settings`.

Thu tu uu tien khi nap gia tri (theo pydantic-settings):
  1. Bien moi truong that (os.environ) -- uu tien cao nhat, dung cho
     production / CI-CD (khong dung file .env tren server that).
  2. File `.env` o thu muc goc `agent/` -- CHI dung cho local dev, khong
     commit (`.env` phai nam trong .gitignore). Xem `.env.example`
     de biet cac bien can khai bao.
  3. Gia tri default khai bao trong cac class ben duoi.

QUY TAC KE THUA SETTINGS (ap dung cho moi Settings class them sau nay):
  - MOI class Settings con PHAI ke thua tu `_BaseAppSettings` ben duoi,
    KHONG ke thua truc tiep tu `BaseSettings` cua pydantic_settings.
  - `_BaseAppSettings` la noi DUY NHAT khai bao `env_file`, encoding,
    va `extra="ignore"`. Class con chi khai bao them `env_prefix` rieng
    cua minh -- pydantic tu dong merge model_config qua ke thua (da
    kiem chung: cac key khong trung se duoc gop, key trung se lay gia
    tri cua class con).
  - Neu sau nay can doi vi tri file .env, hoac doi encoding, CHI sua
    o `_BaseAppSettings`, KHONG sua tung class con.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Duong dan TUYET DOI toi file .env, luon nam o thu muc goc cua `agent/`
# (cha cua thu muc `config/` chua file nay). Dung tuyet doi thay vi
# chuoi ".env" tuong doi -- vi ".env" tuong doi phu thuoc vao thu muc
# dang dung khi chay lenh (cwd), se gay loi kho hieu neu chay pytest/
# uvicorn tu mot thu muc khac (vd: tu thu muc goc du an beyond-intelligence
# thay vi tu agent/, du quy uoc du an la luon chay tu agent/).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class _BaseAppSettings(BaseSettings):
    """
    Base chung cho MOI Settings class trong du an.

    Tap trung env_file/encoding/extra tai MOT noi duy nhat -- moi
    Settings class con (LLMSettings, DecisionPolicySettings...) ke
    thua tu day thay vi tu BaseSettings truc tiep, va CHI can khai
    them them env_prefix rieng cua minh.
    """

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
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"  # dung cho test/dev khong can goi API that


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LLMSettings(_BaseAppSettings):
    """
    Cau hinh cho LLM provider dang dung -- doc boi infrastructure/llm/*
    (GeminiProvider, MockLLM...). KHONG doc truc tiep boi domain/application.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: LLMProvider = LLMProvider.GEMINI
    # gemini-2.0-flash da bi Google khai tu 1/6/2026. Dong 3.x hien tai
    # (8/2026): gemini-3.6-flash (GA, mac dinh -- nhanh & re), 3.5-flash-lite
    # (GA, re nhat), gemini-3.1-pro-preview (preview, reasoning sau hon
    # nhung Google co the doi model dang sau ten nay bat ky luc nao).
    model: str = "gemini-3.6-flash"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    # Dong model Gemini 3.x mac dinh bat "thinking" (suy luan an) truoc
    # khi tra loi, tieu ton token vao max_tokens -- neu max_tokens nho
    # (vd: cac buoc pipeline can tra loi ngan gon) co the tieu het vao
    # thinking, khong con token cho cau tra loi that (finish_reason=
    # MAX_TOKENS, content rong). "low" la muc an toan mac dinh cho agent
    # can output nhanh/on dinh; doi "high" cho buoc can reasoning sau
    # (vd: Generate Strategy) qua env LLM_THINKING_LEVEL.
    thinking_level: str = "low"

    # Secret -- luon la SecretStr, luon tu env, khong co default that.
    gemini_api_key: SecretStr | None = Field(default=None)
    openai_api_key: SecretStr | None = Field(default=None)
    anthropic_api_key: SecretStr | None = Field(default=None)

    def require_api_key(self) -> SecretStr:
        """
        Lay API key tuong ung provider dang chon trong `provider`, bao
        loi ro rang ngay tu dau neu thieu -- thay vi de loi mo ho tu
        ben trong Gemini/OpenAI SDK khi request that bai.
        """
        key_map: dict[LLMProvider, SecretStr | None] = {
            LLMProvider.GEMINI: self.gemini_api_key,
            LLMProvider.OPENAI: self.openai_api_key,
            LLMProvider.ANTHROPIC: self.anthropic_api_key,
        }
        key = key_map.get(self.provider)
        if key is None:
            raise ValueError(
                f"Thieu API key cho provider '{self.provider.value}'. "
                f"Hay set bien moi truong LLM_{self.provider.value.upper()}_API_KEY "
                f"(vd: LLM_GEMINI_API_KEY=... trong file .env)."
            )
        return key


class DecisionPolicySettings(_BaseAppSettings):
    """Cau hinh nguong cho DecisionPolicy (domain/policies/decision_policy.py)."""

    model_config = SettingsConfigDict(env_prefix="DECISION_")

    auto_execute_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    reject_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    allow_high_risk_auto_execute: bool = False

    @field_validator("reject_threshold")
    @classmethod
    def _reject_below_auto_execute(cls, v: float, info) -> float:
        auto = info.data.get("auto_execute_threshold")
        if auto is not None and v >= auto:
            raise ValueError(
                "DECISION_REJECT_THRESHOLD phai nho hon DECISION_AUTO_EXECUTE_THRESHOLD"
            )
        return v


class RetryPolicySettings(_BaseAppSettings):
    """Cau hinh cho RetryPolicy (domain/policies/retry_policy.py)."""

    model_config = SettingsConfigDict(env_prefix="RETRY_")

    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay_seconds: float = Field(default=1.0, gt=0)
    max_delay_seconds: float = Field(default=30.0, gt=0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)


class ToolPolicySettings(_BaseAppSettings):
    """Cau hinh mac dinh cho ToolPolicy (domain/policies/tool_policy.py)."""

    model_config = SettingsConfigDict(env_prefix="TOOL_")

    auto_deny_unknown_tools: bool = True


class ObservabilitySettings(_BaseAppSettings):
    """Cau hinh logging/tracing -- doc boi observability/*."""

    model_config = SettingsConfigDict(env_prefix="OBSERVABILITY_")

    log_level: LogLevel = LogLevel.INFO
    log_prompts: bool = False  # mac dinh KHONG log full prompt -- tranh ro du lieu nhay cam
    tracing_enabled: bool = False
    tracing_endpoint: str | None = None


class Settings(_BaseAppSettings):
    """
    Nguon cau hinh goc, gop tat ca nhom con o tren.

    Ke thua tu _BaseAppSettings giong het cac class con khac -- khong
    can khai bao lai env_file/encoding/extra o day nua.

    Import instance `settings` da khoi tao san o cuoi file nay va dung
    lai; KHONG tu goi `Settings()` o noi khac trong code (se doc lai
    .env nhieu lan, co the khong dong bo giua cac module).
    """

    app_name: str = "beyond-intelligence-agent"
    environment: Environment = Environment.DEVELOPMENT

    llm: LLMSettings = Field(default_factory=LLMSettings)
    decision_policy: DecisionPolicySettings = Field(default_factory=DecisionPolicySettings)
    retry_policy: RetryPolicySettings = Field(default_factory=RetryPolicySettings)
    tool_policy: ToolPolicySettings = Field(default_factory=ToolPolicySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    # Application behavior chung, khong thuoc rieng nhom nao o tren.
    max_iterations: int = Field(default=10, ge=1, le=100)
    retrieval_top_k: int = Field(default=5, ge=1, le=50)

    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


# Instance duy nhat, dung chung cho toan bo agent/.
# Import: `from config.settings import settings`
settings = Settings()