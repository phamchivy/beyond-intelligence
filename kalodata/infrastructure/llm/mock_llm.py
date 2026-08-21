"""
Vi tri file nay: data/infrastructure/llm/mock_llm.py

MockLLM -- ban rieng cua data/, cung pattern nhu agent/infrastructure/llm/mock_llm.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from domain.ports.llm import LLMRequest, LLMResponse, TokenUsage


@dataclass
class MockLLM:
    fixed_response: str | None = None
    response_queue: list[LLMResponse] = field(default_factory=list)
    raise_error: Exception | None = None
    model_name: str = "mock-llm"

    call_history: list[LLMRequest] = field(default_factory=list, init=False)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.call_history.append(request)

        if self.raise_error is not None:
            raise self.raise_error

        if self.response_queue:
            return self.response_queue.pop(0)

        content = self.fixed_response if self.fixed_response is not None else "mock response"
        return LLMResponse(
            content=content,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
            model=self.model_name,
        )

    @property
    def call_count(self) -> int:
        return len(self.call_history)