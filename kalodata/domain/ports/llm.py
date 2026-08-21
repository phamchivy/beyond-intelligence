"""
Vi tri file nay: data/domain/ports/llm.py

LLM Port -- ban rieng cua data/ (khong import tu agent/, 2 container
doc lap). Dinh nghia y het nguyen tac: domain chi biet Protocol nay,
khong biet Gemini/DeepSeek SDK cu the.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0 or self.completion_tokens < 0:
            raise ValueError("Token counts cannot be negative")

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        if not isinstance(other, TokenUsage):
            return NotImplemented
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
        )


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    temperature: float = 0.2
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = "stop"


@runtime_checkable
class LLM(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...