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
from domain.ports.memory import Memory, MemoryItem
from domain.ports.tool import Tool, ToolResult
from observability.logging import get_logger, log_duration, log_event

logger = get_logger(__name__)

_PENDING_ACTIONS_NAMESPACE = "pending_actions"


class ToolExecutionStatus(str, Enum):
    EXECUTED = "executed"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"
    UNKNOWN_TOOL = "unknown_tool"
    NOT_FOUND = "not_found"  # approve() goi voi call_id khong/khong con ton tai


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

    `memory` la tham so TUY CHON (Optional Dependency): neu duoc truyen
    vao, moi ToolCall roi vao trang thai PENDING_APPROVAL se duoc luu
    lai qua Memory port (namespace "pending_actions"), de sau nay --
    co the la mot request HTTP hoan toan khac, tu Backend, sau khi
    nguoi dung bam duyet tren giao dien -- co the goi `approve(call_id)`
    de tim lai va thuc thi, KHONG can Agent van dang "cho" trong bo nho.

    Neu khong truyen `memory` (mac dinh None), ToolExecutor van hoat
    dong nhu truoc: nguoi goi tu chiu trach nhiem giu lai `tool_call`
    tu ToolExecutionOutcome de tu goi execute_approved() sau nay.
    """

    def __init__(
        self,
        tools: dict[str, Tool],
        tool_policy: ToolPolicy,
        memory: Memory | None = None,
    ) -> None:
        self._tools = tools
        self._tool_policy = tool_policy
        self._memory = memory

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
            # KHONG tu thuc thi -- luu lai (neu co Memory) de sau nay
            # `approve(call_id)` co the tim lai va thuc thi, du la tu
            # mot request/tien trinh khac hoan toan voi lan goi nay.
            if self._memory is not None:
                await self._memory.save(
                    MemoryItem(
                        key=tool_call.call_id,
                        value=tool_call,
                        namespace=_PENDING_ACTIONS_NAMESPACE,
                    )
                )
                log_event(
                    logger, "info", "pending_action_saved", call_id=tool_call.call_id
                )
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

    async def approve(self, call_id: str) -> ToolExecutionOutcome:
        """
        Tim lai mot ToolCall dang cho duyet (da luu qua Memory khi
        execute() tra ve PENDING_APPROVAL) bang `call_id`, roi thuc thi
        qua execute_approved().

        Day la diem vao danh cho Backend: nguoi dung bam [APPROVE & FIX]
        tren giao dien -> Backend chi can goi `approve(call_id)`, khong
        can tu quan ly lai toan bo ToolCall.

        Neu ToolExecutor khong duoc khoi tao voi `memory` (memory=None),
        ham nay luon tra ve NOT_FOUND -- vi khong co noi nao de tim lai
        ToolCall theo call_id ca. Trong truong hop do, nguoi goi phai tu
        giu ToolCall va goi thang execute_approved(tool_call).
        """
        if self._memory is None:
            log_event(
                logger,
                "warning",
                "approve_called_without_memory",
                call_id=call_id,
            )
            return ToolExecutionOutcome(
                status=ToolExecutionStatus.NOT_FOUND,
                tool_call=ToolCall(tool_name="", arguments={}, call_id=call_id),
            )

        item = await self._memory.get(call_id, namespace=_PENDING_ACTIONS_NAMESPACE)
        if item is None:
            log_event(logger, "warning", "pending_action_not_found", call_id=call_id)
            return ToolExecutionOutcome(
                status=ToolExecutionStatus.NOT_FOUND,
                tool_call=ToolCall(tool_name="", arguments={}, call_id=call_id),
            )

        tool_call: ToolCall = item.value
        outcome = await self.execute_approved(tool_call)

        # Xoa khoi danh sach cho duyet sau khi da xu ly (du thanh cong
        # hay bi DENY) -- khong de mot pending action bi "duyet" hai lan.
        await self._memory.delete(call_id, namespace=_PENDING_ACTIONS_NAMESPACE)

        return outcome