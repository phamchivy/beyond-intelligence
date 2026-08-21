"""
Agent -- vong lap orchestration chinh. THEO DUNG nguyen tac "Agent phai
cuc ky mong" da thong nhat trong tai lieu kien truc: Agent KHONG tu goi
LLM, KHONG tu goi Tool, KHONG tu ghi log -- chi dieu phoi ReasoningService
va ToolExecutor, roi tong hop thanh Decision cuoi cung qua DecisionPolicy.

Vong lap kieu ReAct don gian: hoi LLM buoc tiep theo -> neu la tool_call
thi thuc thi (qua ToolExecutor, co kiem soat ToolPolicy) roi lap lai;
neu la final_answer thi dung va tao Decision.
"""
from __future__ import annotations

from application.context.context_builder import ContextBuilder
from application.execution.executor import ToolExecutionStatus, ToolExecutor
from application.reasoning.reasoning_service import ReasoningService, ReasoningStepKind
from domain.entities.agent_state import AgentState, Observation, StepStatus
from domain.entities.decision import Decision
from domain.entities.task import Task
from domain.ports.llm import ToolDefinition
from domain.value_objects.token_usage import TokenUsage
from observability.logging import get_logger, log_event

logger = get_logger(__name__)


class MaxIterationsExceededError(Exception):
    """Agent chay qua so buoc toi da (settings.max_iterations) ma chua co final_answer."""


class Agent:
    """
    Dieu phoi mot lan chay hoan chinh: Task -> AgentState -> vong lap
    reasoning/tool -> Decision.

    Nhan moi dependency qua constructor (Dependency Injection) -- KHONG
    tu tao ReasoningService/ToolExecutor ben trong. Noi duy nhat duoc
    lap rap cac dependency nay la agent_factory.py / bootstrap/container.py.
    """

    def __init__(
        self,
        reasoning_service: ReasoningService,
        tool_executor: ToolExecutor,
        available_tools: tuple[ToolDefinition, ...] = (),
        max_iterations: int = 10,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._reasoning_service = reasoning_service
        self._tool_executor = tool_executor
        self._available_tools = available_tools
        self._max_iterations = max_iterations
        self._context_builder = context_builder

    async def run(self, task: Task) -> Decision:
        from domain.entities.context import Context  # tranh vong lap import o muc module

        log_event(logger, "info", "agent_run_started", task_id=task.id, goal=task.goal)
        context = await self._context_builder.build(task) if self._context_builder else Context()
        state = AgentState(task=task, context=context)

        for iteration in range(self._max_iterations):
            step = await self._reasoning_service.decide_next_step(state, self._available_tools)

            if step.kind == ReasoningStepKind.FINAL_ANSWER:
                decision = self._to_decision(state, step.llm_response.content, step.token_usage)
                log_event(
                    logger,
                    "info",
                    "agent_run_completed",
                    task_id=task.id,
                    iterations=iteration + 1,
                    decision_action=decision.action,
                    confidence=decision.confidence,
                )
                return decision

            # kind == TOOL_CALL -- xu ly TUNG tool_call LLM yeu cau
            # trong response nay (co the co nhieu tool_call cung luc).
            for tool_call in step.llm_response.tool_calls:
                outcome = await self._tool_executor.execute(tool_call)
                state = state.with_observation(
                    Observation(
                        step_id=f"step-{state.current_step}",
                        source=f"tool:{tool_call.tool_name}",
                        content=self._describe_outcome(outcome),
                    )
                )

        log_event(logger, "error", "agent_run_max_iterations_exceeded", task_id=task.id, max_iterations=self._max_iterations)
        raise MaxIterationsExceededError(
            f"Agent vuot qua {self._max_iterations} buoc ma chua co cau tra loi cuoi cung "
            f"cho task '{task.id}'."
        )

    @staticmethod
    def _describe_outcome(outcome) -> str:  # noqa: ANN001 -- ToolExecutionOutcome, tranh import vong
        if outcome.status == ToolExecutionStatus.EXECUTED:
            return f"ket qua: {outcome.result.output if outcome.result else None}"
        if outcome.status == ToolExecutionStatus.DENIED:
            return "bi tu choi boi ToolPolicy (khong duoc phep goi tool nay)"
        if outcome.status == ToolExecutionStatus.PENDING_APPROVAL:
            return "dang cho nguoi dung phe duyet truoc khi thuc thi"
        return "tool khong ton tai trong registry"

    @staticmethod
    def _to_decision(state: AgentState, content: str, token_usage: TokenUsage) -> Decision:
        """
        Tao Decision tu cau tra loi cuoi cung cua LLM.

        Ghi chu: confidence hien dang gan mot gia tri mac dinh co ban
        (0.7) vi buoc trich xuat confidence co cau truc tu LLM (vd: bat
        LLM tra ve JSON co field confidence rieng) chua duoc trien khai
        o day -- se hoan thien khi lam Decision Model chi tiet hon
        (structured output). DecisionPolicy van ap dung dung tren gia
        tri nay, chi la do chinh xac cua confidence se duoc cai thien sau.
        """
        return Decision(
            action=f"respond:{state.task.id}",
            recommendation=content,
            confidence=0.7,
            evidence=tuple(
                f"[{obs.source}] {obs.content}" for obs in state.observations
            ),
        )