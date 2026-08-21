"""
Vi tri file nay: data/bootstrap/container.py

Composition Root DUY NHAT cua toan bo data/ -- cung nguyen tac da ap
dung cho agent/bootstrap/container.py.
"""
from __future__ import annotations

from application.services.insight_service import InsightService
from config.settings import LLMProvider, Settings
from config.settings import settings as _default_settings
from domain.policies.retry_policy import RetryPolicy
from domain.ports.llm import LLM
from domain.ports.market_data_provider import MarketDataDomain, MarketDataProvider
from infrastructure.kalodata.kalodata_client import KalodataClient
from infrastructure.kalodata.mock_kalodata_client import MockKalodataClient
from infrastructure.llm.deepseek_provider import DeepSeekProvider
from infrastructure.llm.gemini_provider import GeminiProvider
from infrastructure.llm.mock_llm import MockLLM


def _build_llm(config: Settings) -> LLM:
    if config.llm.provider == LLMProvider.MOCK:
        return MockLLM()
    if config.llm.provider == LLMProvider.GEMINI:
        return GeminiProvider(config=config.llm)
    if config.llm.provider == LLMProvider.DEEPSEEK:
        return DeepSeekProvider(config=config.llm)
    raise ValueError(f"LLM provider '{config.llm.provider.value}' chua duoc ho tro.")


def _build_market_data_provider(config: Settings, use_mock: bool = False) -> MarketDataProvider:
    if use_mock:
        return MockKalodataClient()
    return KalodataClient(config=config.kalodata)


def _build_retry_policy(config: Settings) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=config.retry_policy.max_attempts,
        base_delay_seconds=config.retry_policy.base_delay_seconds,
        max_delay_seconds=config.retry_policy.max_delay_seconds,
        backoff_multiplier=config.retry_policy.backoff_multiplier,
    )


def _parse_domains(config: Settings) -> list[MarketDataDomain]:
    """
    Doc `settings.insight_domains` (chuoi phan cach dau phay, vd
    "video,product,category") thanh danh sach MarketDataDomain -- noi
    DUY NHAT parse chuoi nay, tranh lap logic o InsightService.
    """
    raw = config.insight_domains.strip()
    if not raw:
        return [MarketDataDomain.VIDEO, MarketDataDomain.PRODUCT]
    return [MarketDataDomain(name.strip()) for name in raw.split(",") if name.strip()]


def build_insight_service(config: Settings | None = None) -> InsightService:
    cfg = config or _default_settings
    use_mock_kalodata = cfg.llm.provider == LLMProvider.MOCK

    return InsightService(
        llm=_build_llm(cfg),
        market_data_provider=_build_market_data_provider(cfg, use_mock=use_mock_kalodata),
        retry_policy=_build_retry_policy(cfg),
        max_revisions=cfg.max_insight_revisions,
        ranking_page_size=cfg.ranking_page_size,
        top_n_for_detail=cfg.top_n_for_detail,
        domains=_parse_domains(cfg),
    )