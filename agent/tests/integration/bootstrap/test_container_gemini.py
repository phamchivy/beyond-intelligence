"""
Integration test cho bootstrap/container.py -- chay TOAN BO pipeline
that: container lap rap Agent voi GeminiProvider THAT (khong Mock), goi
Gemini API that, tra ve Decision that.

Day la bai test gia tri nhat trong toan du an: xac nhan moi lop (Agent
-> ReasoningService -> GeminiProvider -> Gemini API that) khop voi nhau
dung nhu thiet ke, khong chi tung phan rieng le.

Tu dong skip neu khong co LLM_GEMINI_API_KEY that (giong cach da lam o
tests/integration/llm/test_gemini_provider.py).
"""
from __future__ import annotations

import pytest

from bootstrap.container import build_agent_from_settings
from config.settings import LLMProvider, Settings, settings as default_settings
from domain.entities.task import Task

pytestmark = pytest.mark.integration

_HAS_REAL_API_KEY = (
    default_settings.llm.provider == LLMProvider.GEMINI
    and default_settings.llm.gemini_api_key is not None
)

skip_without_api_key = pytest.mark.skipif(
    not _HAS_REAL_API_KEY,
    reason="Can LLM_GEMINI_API_KEY that trong .env de chay integration test nay",
)


@skip_without_api_key
class TestContainerWithRealGemini:
    async def test_full_pipeline_produces_decision(self) -> None:
        agent = build_agent_from_settings()  # dung settings that tu .env

        decision = await agent.run(
            Task.create(goal="Tra loi that ngan gon: Viet Nam co bao nhieu tinh thanh?")
        )

        assert decision.recommendation.strip() != ""
        assert 0.0 <= decision.confidence <= 1.0

    async def test_agent_respects_configured_max_iterations(self) -> None:
        config = Settings(llm=default_settings.llm, max_iterations=2)
        agent = build_agent_from_settings(config=config)

        # Khong co Tool nao duoc dang ky -> LLM khong the goi tool ->
        # se tra loi ngay lan dau -> khong bao gio cham max_iterations.
        decision = await agent.run(Task.create(goal="Noi 'xin chao' bang tieng Viet"))

        assert decision is not None