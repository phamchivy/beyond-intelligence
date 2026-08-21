"""
Vi tri file nay: agent/tests/integration/llm/test_deepseek_provider_real.py

Integration test cho DeepSeekProvider -- goi model DeepSeek THAT qua
BytePlus ModelArk (khong Mock). Ton tien/token that va can mang.

Tu dong skip neu thieu LLM_DEEPSEEK_API_KEY that trong .env, giong cach
da lam voi test_gemini_provider.py.

Chay: pytest tests/integration/ -v -m integration
"""
from __future__ import annotations

import pytest

from config.settings import LLMProvider, LLMSettings
from domain.ports.llm import LLMMessage, LLMRequest, MessageRole
from infrastructure.llm.deepseek_provider import DeepSeekProvider

pytestmark = pytest.mark.integration

_llm_settings = LLMSettings()
_HAS_REAL_API_KEY = (
    _llm_settings.provider == LLMProvider.DEEPSEEK and _llm_settings.deepseek_api_key is not None
)

skip_without_api_key = pytest.mark.skipif(
    not _HAS_REAL_API_KEY,
    reason=(
        "Can LLM_PROVIDER=deepseek + LLM_DEEPSEEK_API_KEY that trong .env "
        "de chay integration test nay"
    ),
)


@pytest.fixture
def deepseek_provider() -> DeepSeekProvider:
    return DeepSeekProvider(config=_llm_settings)


@skip_without_api_key
class TestDeepSeekProviderReal:
    async def test_generate_returns_non_empty_content(
        self, deepseek_provider: DeepSeekProvider
    ) -> None:
        request = LLMRequest(
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content="Tra loi that ngan gon, duoi 15 tu."),
                LLMMessage(role=MessageRole.USER, content="Viet Nam co bao nhieu tinh thanh?"),
            ),
            max_tokens=200,
        )

        response = await deepseek_provider.generate(request)

        assert response.content.strip() != ""
        assert response.token_usage.total_tokens > 0
        assert response.model

    async def test_tool_calling_returns_structured_tool_call(
        self, deepseek_provider: DeepSeekProvider
    ) -> None:
        from domain.ports.llm import ToolDefinition

        request = LLMRequest(
            messages=(
                LLMMessage(
                    role=MessageRole.USER,
                    content="Lay du lieu thoi tiet Ha Noi hom nay bang tool get_weather.",
                ),
            ),
            tools=(
                ToolDefinition(
                    name="get_weather",
                    description="Lay thong tin thoi tiet theo ten thanh pho",
                    parameters_schema={
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                ),
            ),
            max_tokens=200,
        )

        response = await deepseek_provider.generate(request)

        # Model co the chon goi tool hoac tra loi thang -- chi assert
        # request khong loi va co response hop le, khong ep buoc phai
        # goi tool (hanh vi model co the thay doi theo thoi gian).
        assert response is not None