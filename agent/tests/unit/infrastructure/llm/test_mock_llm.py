"""
Unit test cho MockLLM -- khong goi mang, khong can API key, chay nhanh.

Muc dich chinh cua bo test nay:
  1. Xac nhan MockLLM tuan thu dung Protocol LLM (domain/ports/llm.py) --
     day la bai kiem tra "hop dong" quan trong nhat: neu MockLLM khong
     khop Protocol, moi test dung MockLLM de gia lap Agent sau nay se
     sai lech so voi thuc te khi doi sang GeminiProvider that.
  2. Xac nhan cac che do gia lap (fixed response / response queue / loi)
     hoat dong dung, vi day la cong cu test nen tang cho toan bo cac
     test khac o application layer sau nay.
"""
from __future__ import annotations

import pytest

from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.llm import LLM, LLMMessage, LLMRequest, LLMResponse, MessageRole
from infrastructure.llm.mock_llm import MockLLM


def _simple_request(text: str = "hello") -> LLMRequest:
    return LLMRequest(messages=(LLMMessage(role=MessageRole.USER, content=text),))


class TestMockLLMConformsToPort:
    def test_mock_llm_satisfies_llm_protocol(self) -> None:
        llm = MockLLM()
        assert isinstance(llm, LLM)


class TestFixedResponse:
    async def test_returns_fixed_response_content(self) -> None:
        llm = MockLLM(fixed_response="Xin chao")
        response = await llm.generate(_simple_request())

        assert response.content == "Xin chao"
        assert response.model == "mock-llm"
        assert response.token_usage.total_tokens > 0

    async def test_returns_default_response_when_nothing_configured(self) -> None:
        llm = MockLLM()
        response = await llm.generate(_simple_request())

        assert response.content == "mock response"


class TestResponseQueue:
    async def test_returns_responses_in_order(self) -> None:
        llm = MockLLM(
            response_queue=[
                LLMResponse(content="buoc 1: phat hien co hoi"),
                LLMResponse(content="buoc 2: phan tich doi thu"),
            ]
        )

        first = await llm.generate(_simple_request("step1"))
        second = await llm.generate(_simple_request("step2"))

        assert first.content == "buoc 1: phat hien co hoi"
        assert second.content == "buoc 2: phan tich doi thu"

    async def test_falls_back_to_default_when_queue_exhausted(self) -> None:
        llm = MockLLM(response_queue=[LLMResponse(content="chi mot buoc")])

        await llm.generate(_simple_request())
        second = await llm.generate(_simple_request())

        assert second.content == "mock response"


class TestErrorSimulation:
    async def test_raises_retryable_error(self) -> None:
        llm = MockLLM(raise_error=RetryableError("timeout gia lap"))

        with pytest.raises(RetryableError):
            await llm.generate(_simple_request())

    async def test_raises_non_retryable_error(self) -> None:
        llm = MockLLM(raise_error=NonRetryableError("sai api key gia lap"))

        with pytest.raises(NonRetryableError):
            await llm.generate(_simple_request())


class TestCallHistory:
    async def test_tracks_call_count_and_history(self) -> None:
        llm = MockLLM(fixed_response="ok")

        await llm.generate(_simple_request("first"))
        await llm.generate(_simple_request("second"))

        assert llm.call_count == 2
        assert llm.call_history[0].messages[0].content == "first"
        assert llm.call_history[1].messages[0].content == "second"

    async def test_reset_clears_history(self) -> None:
        llm = MockLLM(fixed_response="ok")
        await llm.generate(_simple_request())
        assert llm.call_count == 1

        llm.reset()

        assert llm.call_count == 0