"""
ReasoningService -- lop duy nhat trong application/ duoc goi truc tiep
den LLM port. Nhiem vu: tu AgentState hien tai + danh sach Tool kha
dung, xay LLMRequest, goi LLM, va dich LLMResponse thanh mot trong hai
loai ket qua ro rang:

  - ReasoningStep(kind=TOOL_CALL, ...)  -- LLM muon goi tool truoc khi
    tra loi (dung khi con thieu thong tin, vd: can truy xuat lich su
    kenh, can quet compliance...).
  - ReasoningStep(kind=FINAL_ANSWER, ...) -- LLM da du du lieu de dua
    ra cau tra loi/quyet dinh cuoi cung.

Retry o day KHONG tu viet vong lap rieng -- dung RetryPolicy chung
(domain/policies/retry_policy.py), dung 1 noi quyet dinh retry trong
toan he thong, tranh "retry chong retry" da neu trong tai lieu kien truc.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from config.settings import settings
from domain.entities.agent_state import AgentState
from domain.policies.retry_policy import NonRetryableError, RetryableError, RetryPolicy
from domain.ports.llm import (
    LLM,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    MessageRole,
    ToolDefinition,
)
from domain.value_objects.token_usage import TokenUsage
from observability.logging import get_logger, log_duration, log_event

logger = get_logger(__name__)


class ReasoningStepKind(str, Enum):
    TOOL_CALL = "tool_call"
    FINAL_ANSWER = "final_answer"


@dataclass(frozen=True, slots=True)
class ReasoningStep:
    """Ket qua chuan hoa cua mot lan goi LLM trong vong lap reasoning."""

    kind: ReasoningStepKind
    llm_response: LLMResponse

    @property
    def token_usage(self) -> TokenUsage:
        return self.llm_response.token_usage


class ReasoningService:
    """
    Boc LLM port + RetryPolicy thanh mot buoc reasoning duy nhat de
    Agent (application/agent/agent.py) goi, khong phai tu quan ly
    retry/prompt construction rai rac o nhieu noi.
    """

    def __init__(
        self,
        llm: LLM,
        retry_policy: RetryPolicy,
        system_prompt: str = "",
    ) -> None:
        self._llm = llm
        self._retry_policy = retry_policy
        self._system_prompt = system_prompt

    async def decide_next_step(
        self,
        state: AgentState,
        available_tools: tuple[ToolDefinition, ...] = (),
    ) -> ReasoningStep:
        """
        Xay LLMRequest tu AgentState hien tai (task + context + lich su
        observation), goi LLM (co retry theo RetryPolicy), tra ve
        ReasoningStep da phan loai.

        Neu response co tool_calls -> TOOL_CALL (chua phai cau tra loi
        cuoi, con buoc trung gian). Nguoc lai -> FINAL_ANSWER.
        """
        request = self._build_request(state, available_tools)
        if settings.observability.log_prompts:
            log_event(logger, "debug", "llm_request_built", messages=[m.content for m in request.messages])
        response = await self._call_with_retry(request)

        kind = (
            ReasoningStepKind.TOOL_CALL
            if response.tool_calls
            else ReasoningStepKind.FINAL_ANSWER
        )
        return ReasoningStep(kind=kind, llm_response=response)

    def _build_request(
        self, state: AgentState, available_tools: tuple[ToolDefinition, ...]
    ) -> LLMRequest:
        messages: list[LLMMessage] = []

        if self._system_prompt:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=self._system_prompt))

        if state.context.retrieved_documents:
            reference_block = "\n\n".join(doc.content for doc in state.context.retrieved_documents)
            messages.append(
                LLMMessage(
                    role=MessageRole.SYSTEM,
                    content=f"Reference trending videos (RAG):\n\n{reference_block}",
                )
            )

        messages.append(LLMMessage(role=MessageRole.USER, content=state.task.goal))

        # Dua lich su observation vao hoi thoai de LLM biet nhung gi da
        # lam roi (vd: da goi tool nao, ket qua ra sao) truoc khi quyet
        # dinh buoc tiep theo.
        for observation in state.observations:
            messages.append(
                LLMMessage(
                    role=MessageRole.ASSISTANT,
                    content=f"[{observation.source}] {observation.content}",
                )
            )

        return LLMRequest(
            messages=tuple(messages),
            tools=available_tools,
        )

    async def _call_with_retry(self, request: LLMRequest) -> LLMResponse:
        attempt = 0
        last_error: Exception | None = None

        while True:
            attempt += 1
            try:
                with log_duration(logger, "llm_call_completed", attempt=attempt):
                    response = await self._llm.generate(request)
                log_event(
                    logger,
                    "info",
                    "llm_call_result",
                    model=response.model,
                    prompt_tokens=response.token_usage.prompt_tokens,
                    completion_tokens=response.token_usage.completion_tokens,
                    finish_reason=response.finish_reason,
                    tool_call_count=len(response.tool_calls),
                )
                return response
            except (RetryableError, NonRetryableError) as exc:
                last_error = exc
                log_event(
                    logger,
                    "warning",
                    "llm_call_failed",
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                if not self._retry_policy.should_retry(attempt, exc):
                    log_event(logger, "error", "llm_call_gave_up", attempt=attempt)
                    raise
                delay = self._retry_policy.next_delay_seconds(attempt)
                log_event(logger, "info", "llm_call_retrying", attempt=attempt, delay_seconds=delay)
                continue

        raise last_error  # khong bao gio toi day, giu de type-checker yen tam