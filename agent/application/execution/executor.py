"""
ToolExecutor -- lop duy nhat trong application/ duoc phep goi Tool that
su. Moi loi goi tool deu phai di qua day, KHONG duoc Agent tu goi thang
Tool.execute() -- de dam bao moi loi goi deu qua ToolPolicy truoc:

    Planner/ReasoningService -> ToolExecutor -> ToolPolicy -> Tool

Neu ToolPolicy tra ve DENY hoac REQUIRE_APPROVAL, ToolExecutor KHONG tu
quyet dinh thay nguoi dung -- no tra ve ToolExecutionOutcome de tang
tren (Agent) quyet dinh dung lai cho duyet hay bao loi, chu khong tu y
bo qua chinh sach.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.policies.tool_policy import ToolPolicy, ToolPolicyDecision
from domain.ports.llm import ToolCall
from domain.ports.tool import Tool, ToolResult
from observability.logging import get_logger, log_duration, log_event

logger = get_logger(__name__)


class ToolExecutionStatus(str, Enum):
    EXECUTED = "executed"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"
    UNKNOWN_TOOL = "unknown_tool"


@dataclass(frozen=True, slots=True)
class ToolExecutionOutcome:
    """Ket qua cua mot lan yeu cau thuc thi Tool, da qua ToolPolicy."""

    status: ToolExecutionStatus
    tool_call: ToolCall
    result: ToolResult | None = None


class ToolExecutor:
    """
    Registry Tool + ToolPolicy, dung de thuc thi mot ToolCall (do LLM
    yeu cau trong ReasoningStep) mot cach co kiem soat.
    """

    def __init__(self, tools: dict[str, Tool], tool_policy: ToolPolicy) -> None:
        self._tools = tools
        self._tool_policy = tool_policy

    async def execute(self, tool_call: ToolCall) -> ToolExecutionOutcome:
        tool = self._tools.get(tool_call.tool_name)
        if tool is None:
            log_event(logger, "warning", "tool_call_unknown", tool_name=tool_call.tool_name)
            return ToolExecutionOutcome(
                status=ToolExecutionStatus.UNKNOWN_TOOL, tool_call=tool_call
            )

        decision = self._tool_policy.authorize(tool_call.tool_name)
        log_event(
            logger,
            "info",
            "tool_call_authorized",
            tool_name=tool_call.tool_name,
            policy_decision=decision.value,
        )

        if decision == ToolPolicyDecision.DENY:
            return ToolExecutionOutcome(status=ToolExecutionStatus.DENIED, tool_call=tool_call)

        if decision == ToolPolicyDecision.REQUIRE_APPROVAL:
            # KHONG tu thuc thi -- tra ve trang thai cho tang tren (Agent/
            # Backend) hien Action Card cho nguoi dung xac nhan truoc.
            return ToolExecutionOutcome(
                status=ToolExecutionStatus.PENDING_APPROVAL, tool_call=tool_call
            )

        try:
            with log_duration(logger, "tool_call_completed", tool_name=tool_call.tool_name):
                result = await tool.execute(tool_call.arguments)
        except Exception as exc:
            log_event(
                logger,
                "error",
                "tool_call_raised",
                tool_name=tool_call.tool_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        log_event(
            logger,
            "info",
            "tool_call_result",
            tool_name=tool_call.tool_name,
            tool_success=result.success,
        )
        return ToolExecutionOutcome(
            status=ToolExecutionStatus.EXECUTED, tool_call=tool_call, result=result
        )

    async def execute_approved(self, tool_call: ToolCall) -> ToolExecutionOutcome:
        """
        Thuc thi mot ToolCall DA duoc nguoi dung phe duyet tuong minh
        (vd: da bam [APPROVE & FIX] tren Action Card).

        Khac voi execute(): bo qua trang thai REQUIRE_APPROVAL (vi da
        co xac nhan roi, khong can hoi lai). NHUNG van kiem tra DENY --
        chinh sach cam tuyet doi (vd: tool bi vo hieu hoa, hoac khong
        nam trong danh sach cho phep) khong the bi "vuot qua" chi vi
        nguoi dung bam duyet; DENY la quyet dinh he thong, khong phai
        quyet dinh cua tung request.

        Noi goi ham nay: tang Backend, sau khi da tu xac thuc rang
        nguoi dung co quyen va da thuc su bam duyet hanh dong nay --
        KHONG goi tu ReasoningService/vong lap Agent.run() thong thuong.
        """
        tool = self._tools.get(tool_call.tool_name)
        if tool is None:
            log_event(logger, "warning", "tool_call_unknown", tool_name=tool_call.tool_name)
            return ToolExecutionOutcome(
                status=ToolExecutionStatus.UNKNOWN_TOOL, tool_call=tool_call
            )

        decision = self._tool_policy.authorize(tool_call.tool_name)
        log_event(
            logger,
            "info",
            "tool_call_approved_execution",
            tool_name=tool_call.tool_name,
            policy_decision=decision.value,
        )

        if decision == ToolPolicyDecision.DENY:
            # DENY luon thang -- khong the "duyet vuot qua" chinh sach cam.
            return ToolExecutionOutcome(status=ToolExecutionStatus.DENIED, tool_call=tool_call)

        # ALLOW hoac REQUIRE_APPROVAL (da duoc duyet tuong minh) -> thuc thi that.
        try:
            with log_duration(
                logger, "tool_call_completed", tool_name=tool_call.tool_name, via_approval=True
            ):
                result = await tool.execute(tool_call.arguments)
        except Exception as exc:
            log_event(
                logger,
                "error",
                "tool_call_raised",
                tool_name=tool_call.tool_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        log_event(
            logger,
            "info",
            "tool_call_result",
            tool_name=tool_call.tool_name,
            tool_success=result.success,
        )
        return ToolExecutionOutcome(
            status=ToolExecutionStatus.EXECUTED, tool_call=tool_call, result=result
        )