"""
LLM Port -- "hop dong" ma bat ky nha cung cap LLM nao (Gemini, OpenAI,
Anthropic, vLLM...) phai tuan theo de Agent co the su dung.

Day la boundary quan trong nhat he thong: Domain/Application CHI biet
Protocol nay, khong biet Gemini SDK, OpenAI SDK hay chi tiet API cua
tung provider.

Du an nay dung Gemini lam LLM chinh -- nhung port o day KHONG duoc chua
bat ky khai niem rieng cua Gemini (vd: "contents" thay vi "messages",
role "model" thay vi "assistant", generation_config...). Adapter cu the
(infrastructure/llm/gemini_provider.py, code sau) chiu trach nhiem "dich"
giua dinh dang that cua Gemini va LLMRequest/LLMResponse chuan hoa o day.
Nho vay, neu sau nay doi/them OpenAI hay Claude, chi can viet them mot
adapter moi -- Agent/Planner khong doi mot dong nao.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from domain.value_objects.token_usage import TokenUsage


class MessageRole(str, Enum):
    """
    Vai tro chuan hoa cua mot message, khong phu thuoc provider.

    Adapter tu map: vi du GeminiProvider se tu dich ASSISTANT -> "model"
    khi goi API that, con OpenAIProvider giu nguyen "assistant".
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """Mot message trong hoi thoai gui den LLM."""

    role: MessageRole
    content: str
    name: str | None = None  # ten tool, chi dung khi role == TOOL


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """
    Mo ta mot tool ma LLM co the "goi" (function calling), o dang chuan
    hoa -- khong phai dinh dang rieng cua Gemini function_declarations
    hay OpenAI tools.
    """

    name: str
    description: str
    parameters_schema: dict[str, Any] = field(default_factory=dict)  # JSON Schema


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Mot loi goi tool ma LLM yeu cau, xuat hien trong LLMResponse.tool_calls."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Yeu cau chuan hoa gui den bat ky LLM provider nao qua port nay."""

    messages: tuple[LLMMessage, ...]
    temperature: float = 0.2
    max_tokens: int | None = None
    tools: tuple[ToolDefinition, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Ket qua chuan hoa tra ve tu bat ky LLM provider nao qua port nay."""

    content: str
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = "stop"


@runtime_checkable
class LLM(Protocol):
    """
    Port cho kha nang sinh van ban / reasoning cua mot LLM.

    Bat ky adapter nao (GeminiProvider, OpenAIProvider, MockLLM...) chi
    can implement dung method nay la "cam" duoc vao Agent/Planner ma
    khong can sua gi o application/domain layer.
    """

    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...