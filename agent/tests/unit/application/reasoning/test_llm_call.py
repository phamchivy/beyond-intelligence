"""
Vi tri file nay: agent/tests/unit/application/reasoning/test_llm_call.py

Unit test cho call_llm_with_retry -- ham dung chung, tach tu
ReasoningService, gio duoc StoryboardSessionService dung lai. Test truc
tiep tai day de dam bao logic retry dung du duoc goi tu bat ky service
nao.
"""
from __future__ import annotations

import logging

import pytest

from application.reasoning.llm_call import call_llm_with_retry
from domain.policies.retry_policy import NonRetryableError, RetryableError, RetryPolicy
from domain.ports.llm import LLMMessage, LLMRequest, MessageRole
from infrastructure.llm.mock_llm import MockLLM

_logger = logging.getLogger("test_llm_call")


def _request() -> LLMRequest:
    return LLMRequest(messages=(LLMMessage(role=MessageRole.USER, content="hi"),))


class TestSuccess:
    async def test_returns_response_on_first_success(self) -> None:
        llm = MockLLM(fixed_response="ok")

        response = await call_llm_with_retry(llm, _request(), RetryPolicy(), _logger)

        assert response.content == "ok"
        assert llm.call_count == 1


class TestRetry:
    async def test_retries_on_retryable_error_then_succeeds(self) -> None:
        # MockLLM khong ho tro "fail N lan roi thanh cong" san -- mo
        # phong bang subclass nho ngay trong test.
        class FlakyLLM(MockLLM):
            def __init__(self):
                super().__init__(fixed_response="thanh cong")
                self.attempts = 0

            async def generate(self, request):
                self.attempts += 1
                if self.attempts < 2:
                    raise RetryableError("loi tam thoi")
                return await super().generate(request)

        llm = FlakyLLM()
        response = await call_llm_with_retry(llm, _request(), RetryPolicy(max_attempts=3), _logger)

        assert response.content == "thanh cong"
        assert llm.attempts == 2

    async def test_gives_up_after_max_attempts(self) -> None:
        llm = MockLLM(raise_error=RetryableError("luon loi"))

        with pytest.raises(RetryableError):
            await call_llm_with_retry(llm, _request(), RetryPolicy(max_attempts=2), _logger)

    async def test_non_retryable_error_stops_immediately(self) -> None:
        llm = MockLLM(raise_error=NonRetryableError("sai api key"))

        with pytest.raises(NonRetryableError):
            await call_llm_with_retry(llm, _request(), RetryPolicy(max_attempts=5), _logger)

        assert llm.call_count == 1  # khong retry them lan nao