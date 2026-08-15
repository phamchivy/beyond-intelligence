"""
Integration test cho GeminiProvider -- goi Gemini API THAT qua mang.

Khac voi unit test (tests/unit/), bo test nay:
  - Can bien moi truong LLM_GEMINI_API_KEY that -- TU DONG SKIP neu
    khong co (doc qua Settings, nen se TU DONG nhan gia tri tu file
    .env neu ban da khai bao o do -- khong can tu set bien moi truong
    thu cong truoc khi chay pytest).
  - Ton tien/token that (du rat nho) va can ket noi mang.
  - KHONG chay tu dong moi lan `pytest` -- chi chay khi co dinh:
        pytest tests/integration/ -m integration
    hoac chay rieng file nay khi muon xac nhan tich hop that su.

Muc dich: xac nhan viec "dich" giua LLMRequest/LLMResponse chuan hoa va
Gemini SDK that su hoat dong dung -- dieu ma unit test voi MockLLM
KHONG the xac nhan duoc (vi MockLLM khong dung SDK that).
"""
from __future__ import annotations

import pytest

from config.settings import LLMProvider, LLMSettings
from domain.ports.llm import LLMMessage, LLMRequest, MessageRole
from infrastructure.llm.gemini_provider import GeminiProvider

pytestmark = pytest.mark.integration

# Doc qua Settings (pydantic-settings) -- se TU DONG doc ca file .env
# lan bien moi truong that, dung cach nap gia tri giong het luc app
# chay that, khong doc thang os.environ (se bo qua .env).
_llm_settings = LLMSettings()
_HAS_REAL_API_KEY = (
    _llm_settings.provider == LLMProvider.GEMINI
    and _llm_settings.gemini_api_key is not None
)

skip_without_api_key = pytest.mark.skipif(
    not _HAS_REAL_API_KEY,
    reason=(
        "Can LLM_GEMINI_API_KEY that (trong file .env o thu muc chay pytest, "
        "hoac bien moi truong that) de chay integration test nay"
    ),
)


@pytest.fixture
def gemini_provider() -> GeminiProvider:
    return GeminiProvider(config=_llm_settings)


@skip_without_api_key
class TestGeminiProviderReal:
    async def test_generate_returns_non_empty_content(self, gemini_provider: GeminiProvider) -> None:
        request = LLMRequest(
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content="Tra loi that ngan gon, duoi 10 tu."),
                LLMMessage(role=MessageRole.USER, content="Viet Nam co bao nhieu tinh thanh?"),
            ),
            max_tokens=50,
        )

        response = await gemini_provider.generate(request)

        assert response.content.strip() != ""
        assert response.token_usage.total_tokens > 0
        assert response.model  # da gan model name tu config

    async def test_token_usage_is_tracked(self, gemini_provider: GeminiProvider) -> None:
        request = LLMRequest(
            messages=(LLMMessage(role=MessageRole.USER, content="Noi 'xin chao'"),),
            max_tokens=20,
        )

        response = await gemini_provider.generate(request)

        assert response.token_usage.prompt_tokens > 0
        assert response.token_usage.completion_tokens >= 0