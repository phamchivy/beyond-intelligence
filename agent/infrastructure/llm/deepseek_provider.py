"""
DeepSeekProvider -- implementation THAT cua LLM port, goi model DeepSeek
qua BytePlus ModelArk (Ark SDK chinh thuc, dinh dang tuong thich OpenAI
chat completions).

Day la noi DUY NHAT trong toan bo `agent/` duoc phep import
`byteplussdkarkruntime` cho muc dich text generation. Domain va
Application khong biet DeepSeek/BytePlus ton tai -- chi biet Protocol
LLM (domain/ports/llm.py), giong het nguyen tac da ap dung cho
GeminiProvider.

Chon model DeepSeek cu the qua `LLM_MODEL` trong .env (vd:
deepseek-v3-2-251201) -- xem tai lieu "Danh sach mo hinh API ho tro"
de biet cac model DeepSeek hien co tren BytePlus ModelArk.
"""
from __future__ import annotations

from byteplussdkarkruntime import AsyncArk
from byteplussdkarkruntime._exceptions import ArkAPIError, ArkAPIStatusError

from config.settings import LLMSettings
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.llm import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    MessageRole,
    ToolCall,
    ToolDefinition,
)
from domain.value_objects.token_usage import TokenUsage

# BytePlus ModelArk dung dinh dang chat completions tuong thich OpenAI
# -- role "assistant" giu nguyen (khac Gemini can dich sang "model"),
# nen khong can bang dich role rieng nhu GeminiProvider.
_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


class DeepSeekProvider:
    """
    Adapter implement dung Protocol LLM bang cach goi model DeepSeek
    qua BytePlus ModelArk (Ark SDK).

    Khong tu doc `settings` global -- nhan `LLMSettings` qua constructor
    (Dependency Injection), giong het GeminiProvider.
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
        messages = self._to_arkchat_messages(request.messages)
        tools = self._to_arkchat_tools(request.tools) if request.tools else None

        try:
            response = await self._client.chat.completions.create(
                model=self._config.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens or self._config.max_tokens,
                tools=tools,
            )
        except ArkAPIError as exc:
            raise self._translate_error(exc) from exc

        return self._to_llm_response(response)

    # ------------------------------------------------------------------
    # Dich LLMRequest -> dinh dang chat completions (OpenAI-compatible)
    # ------------------------------------------------------------------

    @staticmethod
    def _to_arkchat_messages(messages: tuple[LLMMessage, ...]) -> list[dict]:
        # role chuan hoa (system/user/assistant/tool) trung khop san
        # voi dinh dang OpenAI-compatible -- khong can bang dich nhu
        # Gemini (role "model" vs "assistant").
        return [{"role": m.role.value, "content": m.content} for m in messages]

    @staticmethod
    def _to_arkchat_tools(tools: tuple[ToolDefinition, ...]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            }
            for tool in tools
        ]

    # ------------------------------------------------------------------
    # Dich response -> LLMResponse
    # ------------------------------------------------------------------

    @staticmethod
    def _to_llm_response(response) -> LLMResponse:  # noqa: ANN001 -- ChatCompletion tu Ark SDK
        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            tool_calls.append(
                ToolCall(
                    tool_name=call.function.name,
                    arguments=_safe_parse_json(call.function.arguments),
                    call_id=call.id,
                )
            )

        usage = response.usage
        token_usage = TokenUsage(
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )

        return LLMResponse(
            content=message.content or "",
            tool_calls=tuple(tool_calls),
            token_usage=token_usage,
            model=response.model,
            finish_reason=choice.finish_reason or "stop",
        )

    # ------------------------------------------------------------------
    # Phan loai loi -- cung nguyen tac Anti-Corruption Layer nhu
    # GeminiProvider: dich exception rieng cua Ark SDK thanh loi domain
    # (RetryableError/NonRetryableError), khong de loi SDK ro ri len tren.
    # ------------------------------------------------------------------

    @staticmethod
    def _translate_error(exc: ArkAPIError) -> Exception:
        status_code = exc.status_code if isinstance(exc, ArkAPIStatusError) else None
        if status_code in _RETRYABLE_HTTP_STATUS:
            return RetryableError(f"DeepSeek/BytePlus API loi tam thoi (status={status_code}): {exc}")
        return NonRetryableError(
            f"DeepSeek/BytePlus API loi khong the retry (status={status_code}): {exc}"
        )


def _safe_parse_json(raw: str) -> dict:
    import json

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}