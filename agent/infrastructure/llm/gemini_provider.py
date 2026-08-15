"""
GeminiProvider -- implementation THAT cua LLM port, goi Google Gemini
qua SDK chinh thuc `google-genai`.

Day la noi DUY NHAT trong toan bo `agent/` duoc phep import `google.genai`.
Domain va Application khong biet Gemini ton tai -- chi biet Protocol LLM
(domain/ports/llm.py). Nhiem vu cua class nay CHI la "dich" hai chieu:

    LLMRequest (chuan hoa)  --dich-->  Gemini Content/GenerateContentConfig
    Gemini GenerateContentResponse  --dich-->  LLMResponse (chuan hoa)

Khong doc gia tri cau hinh (model, temperature, api key...) tu bat ky
noi nao khac ngoai `config.settings` -- KHONG hardcode.

Retry KHONG duoc tu viet vong lap o day (xem domain/policies/retry_policy.py
-- ly do vi sao khong de tung adapter tu retry rieng). GeminiProvider chi
co trach nhiem: goi API mot lan, va NEM RA loi da phan loai dung
(RetryableError / NonRetryableError) de tang tren (application layer)
quyet dinh co retry hay khong theo RetryPolicy chung.
"""
from __future__ import annotations

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

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

# Gemini dung role "model" thay vi "assistant" -- day la noi DUY NHAT
# trong code biet den su khac biet nay, khong de lo ra domain/application.
_ROLE_TO_GEMINI = {
    MessageRole.USER: "user",
    MessageRole.ASSISTANT: "model",
    MessageRole.TOOL: "user",  # Gemini khong co role "tool" rieng cho text don gian
}

# Ma loi HTTP coi la co the retry (loi tam thoi phia server/mang) --
# khac voi loi 400 (sai request) hay 403 (sai quyen) la NonRetryable.
_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


class GeminiProvider:
    """
    Adapter implement dung Protocol LLM bang cach goi Gemini API that.

    Khong tu doc `settings` global -- nhan `LLMSettings` qua constructor,
    dung nguyen tac Dependency Injection: noi duy nhat tao GeminiProvider
    voi gia tri that tu settings la `bootstrap/container.py`.
    """

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
            tools=self._to_gemini_tools(request.tools) if request.tools else None,
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

    # ------------------------------------------------------------------
    # Dich LLMRequest -> dinh dang Gemini
    # ------------------------------------------------------------------

    @staticmethod
    def _to_gemini_contents(
        messages: tuple[LLMMessage, ...],
    ) -> tuple[list[genai_types.Content], str | None]:
        """
        Gemini tach rieng system_instruction khoi contents (khac OpenAI/
        Anthropic gop chung vao messages) -- tach ra o day, mot lan duy
        nhat, thay vi de logic nay ro ri sang application layer.
        """
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

    @staticmethod
    def _to_gemini_tools(tools: tuple[ToolDefinition, ...]) -> list[genai_types.Tool]:
        declarations = [
            genai_types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.parameters_schema,
            )
            for tool in tools
        ]
        return [genai_types.Tool(function_declarations=declarations)]

    # ------------------------------------------------------------------
    # Dich GenerateContentResponse -> LLMResponse
    # ------------------------------------------------------------------

    def _to_llm_response(self, response: genai_types.GenerateContentResponse) -> LLMResponse:
        text = response.text or ""
        tool_calls = self._extract_tool_calls(response)
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
            tool_calls=tuple(tool_calls),
            token_usage=token_usage,
            model=self._config.model,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _extract_tool_calls(response: genai_types.GenerateContentResponse) -> list[ToolCall]:
        calls: list[ToolCall] = []
        if not response.candidates:
            return calls

        for index, part in enumerate(response.candidates[0].content.parts or []):
            fn_call = getattr(part, "function_call", None)
            if fn_call is None:
                continue
            calls.append(
                ToolCall(
                    tool_name=fn_call.name,
                    arguments=dict(fn_call.args or {}),
                    call_id=f"{fn_call.name}-{index}",
                )
            )
        return calls

    # ------------------------------------------------------------------
    # Phan loai loi -- day la Anti-Corruption Layer: dich exception rieng
    # cua Gemini SDK thanh loi domain hieu duoc (RetryableError /
    # NonRetryableError), de RetryPolicy o tang application quyet dinh
    # tiep theo lam gi, khong de loi cua Gemini SDK ro ri len tren.
    # ------------------------------------------------------------------

    @staticmethod
    def _translate_error(exc: genai_errors.APIError) -> Exception:
        status_code = getattr(exc, "code", None)
        if status_code in _RETRYABLE_HTTP_STATUS:
            return RetryableError(f"Gemini API loi tam thoi (status={status_code}): {exc}")
        return NonRetryableError(f"Gemini API loi khong the retry (status={status_code}): {exc}")