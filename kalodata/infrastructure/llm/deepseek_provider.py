"""
Vi tri file nay: data/infrastructure/llm/deepseek_provider.py

DeepSeekProvider -- ban rieng cua data/, cung logic da xac nhan chay
that voi agent/infrastructure/llm/deepseek_provider.py: goi model
DeepSeek qua BytePlus ModelArk Responses API (client.responses.create).

Day la noi DUY NHAT trong data/ duoc phep import `byteplussdkarkruntime`.
"""
from __future__ import annotations

import json

from byteplussdkarkruntime import AsyncArk
from byteplussdkarkruntime._exceptions import ArkAPIError, ArkAPIStatusError

from config.settings import LLMSettings
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.llm import LLMMessage, LLMRequest, LLMResponse, MessageRole, TokenUsage

_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}

_ROLE_TO_RESPONSES = {
    MessageRole.SYSTEM: "system",
    MessageRole.USER: "user",
    MessageRole.ASSISTANT: "assistant",
}


class DeepSeekProvider:
    """
    Adapter implement dung Protocol LLM bang cach goi model DeepSeek qua
    BytePlus ModelArk Responses API. Khong tu doc `settings` global --
    nhan `LLMSettings` qua constructor (Dependency Injection).
    """

    def __init__(self, config: LLMSettings) -> None:
        self._config = config
        api_key = config.require_api_key().get_secret_value()
        if not config.base_url:
            raise ValueError(
                "Thieu LLM_BASE_URL -- can cho DeepSeekProvider (endpoint BytePlus ModelArk)."
            )
        self._client = AsyncArk(base_url=config.base_url, api_key=api_key)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        input_items, instructions = self._to_responses_input(request.messages)

        try:
            response = await self._client.responses.create(
                model=self._config.model,
                input=input_items,
                instructions=instructions,
                temperature=request.temperature,
                max_output_tokens=request.max_tokens or self._config.max_tokens,
            )
        except ArkAPIError as exc:
            raise self._translate_error(exc) from exc

        return self._to_llm_response(response)

    @staticmethod
    def _to_responses_input(messages: tuple[LLMMessage, ...]) -> tuple[list[dict], str | None]:
        instruction_parts: list[str] = []
        input_items: list[dict] = []

        for message in messages:
            if message.role == MessageRole.SYSTEM:
                instruction_parts.append(message.content)
                continue
            input_items.append(
                {"type": "message", "role": _ROLE_TO_RESPONSES[message.role], "content": message.content}
            )

        instructions = "\n".join(instruction_parts) if instruction_parts else None
        return input_items, instructions

    @staticmethod
    def _to_llm_response(response) -> LLMResponse:  # noqa: ANN001 -- Response tu Ark SDK
        text_parts: list[str] = []

        for item in response.output:
            if getattr(item, "type", None) == "message":
                for content_part in item.content or []:
                    part_text = getattr(content_part, "text", None)
                    if part_text:
                        text_parts.append(part_text)

        usage = response.usage
        token_usage = TokenUsage(
            prompt_tokens=usage.input_tokens if usage else 0,
            completion_tokens=usage.output_tokens if usage else 0,
        )

        return LLMResponse(
            content="".join(text_parts),
            token_usage=token_usage,
            model=response.model,
            finish_reason=response.status or "completed",
        )

    @staticmethod
    def _translate_error(exc: ArkAPIError) -> Exception:
        status_code = exc.status_code if isinstance(exc, ArkAPIStatusError) else None
        if status_code in _RETRYABLE_HTTP_STATUS:
            return RetryableError(f"DeepSeek/BytePlus API loi tam thoi (status={status_code}): {exc}")
        return NonRetryableError(
            f"DeepSeek/BytePlus API loi khong the retry (status={status_code}): {exc}"
        )