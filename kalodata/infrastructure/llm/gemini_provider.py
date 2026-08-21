"""
Vi tri file nay: data/infrastructure/llm/gemini_provider.py

GeminiProvider -- ban rieng cua data/, cung logic dich nhu
agent/infrastructure/llm/gemini_provider.py (rut gon, data/ khong can
tool-calling vi khong dung ReAct loop, chi can sinh text tong hop).
"""
from __future__ import annotations

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from config.settings import LLMSettings
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.llm import LLMMessage, LLMRequest, LLMResponse, MessageRole, TokenUsage

_ROLE_TO_GEMINI = {
    MessageRole.USER: "user",
    MessageRole.ASSISTANT: "model",
}

_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


class GeminiProvider:
    def __init__(self, config: LLMSettings) -> None:
        self._config = config
        api_key = config.require_api_key().get_secret_value()
        self._client = genai.Client(api_key=api_key)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        contents, system_instruction = self._to_gemini_contents(request.messages)
        generation_config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=request.temperature,
            max_output_tokens=request.max_tokens or self._config.max_tokens,
            thinking_config=genai_types.ThinkingConfig(
                thinking_level=self._config.thinking_level
            ),
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._config.model,
                contents=contents,
                config=generation_config,
            )
        except genai_errors.APIError as exc:
            raise self._translate_error(exc) from exc

        return self._to_llm_response(response)

    @staticmethod
    def _to_gemini_contents(
        messages: tuple[LLMMessage, ...],
    ) -> tuple[list[genai_types.Content], str | None]:
        system_parts: list[str] = []
        contents: list[genai_types.Content] = []

        for message in messages:
            if message.role == MessageRole.SYSTEM:
                system_parts.append(message.content)
                continue
            contents.append(
                genai_types.Content(
                    role=_ROLE_TO_GEMINI[message.role],
                    parts=[genai_types.Part.from_text(text=message.content)],
                )
            )

        system_instruction = "\n".join(system_parts) if system_parts else None
        return contents, system_instruction

    def _to_llm_response(self, response: genai_types.GenerateContentResponse) -> LLMResponse:
        text = response.text or ""
        usage = response.usage_metadata

        token_usage = TokenUsage(
            prompt_tokens=(usage.prompt_token_count if usage else 0) or 0,
            completion_tokens=(usage.candidates_token_count if usage else 0) or 0,
        )

        finish_reason = "stop"
        if response.candidates:
            raw_reason = response.candidates[0].finish_reason
            finish_reason = str(raw_reason) if raw_reason else "stop"

        return LLMResponse(
            content=text,
            token_usage=token_usage,
            model=self._config.model,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _translate_error(exc: genai_errors.APIError) -> Exception:
        status_code = getattr(exc, "code", None)
        if status_code in _RETRYABLE_HTTP_STATUS:
            return RetryableError(f"Gemini API loi tam thoi (status={status_code}): {exc}")
        return NonRetryableError(f"Gemini API loi khong the retry (status={status_code}): {exc}")