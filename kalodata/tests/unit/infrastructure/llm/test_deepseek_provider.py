"""
Vi tri file nay: data/tests/unit/infrastructure/llm/test_deepseek_provider.py

Unit test cho DeepSeekProvider -- chi test cac ham dich tinh, khong goi API that.
"""
from __future__ import annotations

from types import SimpleNamespace

from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.llm import LLMMessage, MessageRole
from infrastructure.llm.deepseek_provider import DeepSeekProvider


class TestToResponsesInput:
    def test_separates_system_message_into_instructions(self) -> None:
        messages = (
            LLMMessage(role=MessageRole.SYSTEM, content="ban la tro ly"),
            LLMMessage(role=MessageRole.USER, content="xin chao"),
        )

        input_items, instructions = DeepSeekProvider._to_responses_input(messages)

        assert instructions == "ban la tro ly"
        assert input_items == [{"type": "message", "role": "user", "content": "xin chao"}]

    def test_no_system_message_gives_none_instructions(self) -> None:
        messages = (LLMMessage(role=MessageRole.USER, content="x"),)

        _, instructions = DeepSeekProvider._to_responses_input(messages)

        assert instructions is None


class TestToLLMResponse:
    def test_extracts_text_from_message_output(self) -> None:
        fake_response = SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[SimpleNamespace(type="output_text", text="cau tra loi")],
                )
            ],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            model="deepseek-v4-flash",
            status="completed",
        )

        result = DeepSeekProvider._to_llm_response(fake_response)

        assert result.content == "cau tra loi"
        assert result.token_usage.prompt_tokens == 10
        assert result.token_usage.completion_tokens == 5

    def test_joins_multiple_text_parts(self) -> None:
        fake_response = SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(type="output_text", text="phan 1. "),
                        SimpleNamespace(type="output_text", text="phan 2."),
                    ],
                )
            ],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
            model="x",
            status="completed",
        )

        result = DeepSeekProvider._to_llm_response(fake_response)

        assert result.content == "phan 1. phan 2."


class TestTranslateError:
    def test_5xx_status_is_retryable(self) -> None:
        from byteplussdkarkruntime._exceptions import ArkAPIStatusError

        exc = ArkAPIStatusError.__new__(ArkAPIStatusError)
        exc.message = "loi gia lap"
        exc.request_id = "req-test"
        exc.status_code = 503

        result = DeepSeekProvider._translate_error(exc)

        assert isinstance(result, RetryableError)

    def test_4xx_status_is_non_retryable(self) -> None:
        from byteplussdkarkruntime._exceptions import ArkAPIStatusError

        exc = ArkAPIStatusError.__new__(ArkAPIStatusError)
        exc.message = "loi gia lap"
        exc.request_id = "req-test"
        exc.status_code = 403

        result = DeepSeekProvider._translate_error(exc)

        assert isinstance(result, NonRetryableError)