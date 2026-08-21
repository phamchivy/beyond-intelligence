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
from domain.policies.retry_policy import RetryPolicy
from domain.ports.llm import (
    LLM,
    LLMMessage,
    LLMRequest,
    MessageRole,
    ToolDefinition,
)
from domain.value_objects.token_usage import TokenUsage
from observability.logging import get_logger, log_event
from application.reasoning.llm_call import call_llm_with_retry

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
        response = await call_llm_with_retry(self._llm, request, self._retry_policy, logger)

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