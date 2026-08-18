"""
Unit test cho ToolExecutor -- tap trung vao 2 phuong thuc:
  - execute(): luong thong thuong trong vong lap reasoning
  - execute_approved(): luong sau khi nguoi dung da bam duyet
    (Human-in-the-Loop) -- day la phan moi, quan trong nhat can test
    ky vi lien quan truc tiep den an toan (khong duoc "duyet vuot qua"
    chinh sach DENY).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from application.execution.executor import ToolExecutionStatus, ToolExecutor
from domain.policies.tool_policy import ToolPermission, ToolPolicy, ToolRiskLevel
from domain.ports.llm import ToolCall
from domain.ports.tool import ToolResult


@dataclass
class FakeTool:
    name: str = "swap_music"
    description: str = "test"
    parameters_schema: dict = field(default_factory=dict)
    call_count: int = field(default=0, init=False)

    async def execute(self, arguments: dict) -> ToolResult:
        self.call_count += 1
        return ToolResult.ok(output="da doi nhac nen thanh cong")


def _call() -> ToolCall:
    return ToolCall(tool_name="swap_music", arguments={}, call_id="c1")


class TestExecuteNormalFlow:
    async def test_low_risk_tool_executes_immediately(self) -> None:
        tool = FakeTool()
        policy = ToolPolicy().with_permission(ToolPermission("swap_music", ToolRiskLevel.LOW))
        executor = ToolExecutor(tools={"swap_music": tool}, tool_policy=policy)

        outcome = await executor.execute(_call())

        assert outcome.status == ToolExecutionStatus.EXECUTED
        assert tool.call_count == 1

    async def test_high_risk_tool_does_not_execute_returns_pending(self) -> None:
        tool = FakeTool()
        policy = ToolPolicy().with_permission(ToolPermission("swap_music", ToolRiskLevel.HIGH))
        executor = ToolExecutor(tools={"swap_music": tool}, tool_policy=policy)

        outcome = await executor.execute(_call())

        assert outcome.status == ToolExecutionStatus.PENDING_APPROVAL
        assert tool.call_count == 0  # TUYET DOI khong duoc thuc thi khi chua duyet


class TestExecuteApproved:
    async def test_high_risk_tool_executes_after_approval(self) -> None:
        """Day la kich ban chinh cua luong HITL: tool bi cho o execute(),
        nhung thuc thi duoc qua execute_approved() sau khi nguoi dung duyet."""
        tool = FakeTool()
        policy = ToolPolicy().with_permission(ToolPermission("swap_music", ToolRiskLevel.HIGH))
        executor = ToolExecutor(tools={"swap_music": tool}, tool_policy=policy)

        pending = await executor.execute(_call())
        assert pending.status == ToolExecutionStatus.PENDING_APPROVAL
        assert tool.call_count == 0

        # Nguoi dung bam [APPROVE & FIX] -> Backend goi execute_approved
        # voi chinh tool_call da nhan duoc tu outcome truoc do.
        approved = await executor.execute_approved(pending.tool_call)

        assert approved.status == ToolExecutionStatus.EXECUTED
        assert tool.call_count == 1
        assert approved.result.output == "da doi nhac nen thanh cong"

    async def test_denied_tool_cannot_be_bypassed_by_approval(self) -> None:
        """Chinh sach cam (DENY) khong the bi 'duyet vuot qua' -- day la
        test quan trong nhat ve mat an toan cua toan bo ToolExecutor."""
        tool = FakeTool()
        policy = ToolPolicy(auto_deny_unknown_tools=True)  # khong khai bao permission -> DENY
        executor = ToolExecutor(tools={"swap_music": tool}, tool_policy=policy)

        outcome = await executor.execute_approved(_call())

        assert outcome.status == ToolExecutionStatus.DENIED
        assert tool.call_count == 0

    async def test_low_risk_tool_also_executes_via_approved_path(self) -> None:
        # execute_approved() van hoat dong dung voi tool LOW risk (ALLOW),
        # khong chi danh rieng cho REQUIRE_APPROVAL.
        tool = FakeTool()
        policy = ToolPolicy().with_permission(ToolPermission("swap_music", ToolRiskLevel.LOW))
        executor = ToolExecutor(tools={"swap_music": tool}, tool_policy=policy)

        outcome = await executor.execute_approved(_call())

        assert outcome.status == ToolExecutionStatus.EXECUTED
        assert tool.call_count == 1

    async def test_unknown_tool_returns_unknown_status(self) -> None:
        policy = ToolPolicy()
        executor = ToolExecutor(tools={}, tool_policy=policy)

        outcome = await executor.execute_approved(_call())

        assert outcome.status == ToolExecutionStatus.UNKNOWN_TOOL


class TestApproveWithMemory:
    """Kich ban quan trong nhat: mo phong dung luong HITL that -- 1 lan
    goi execute() (nhu dang chay trong request A), roi MOT LAN GOI KHAC
    HOAN TOAN (mo phong request B, sau khi nguoi dung bam duyet) chi
    dung call_id de tim lai va thuc thi -- khong con giu tool_call trong
    bo nho cua request A nua."""

    async def test_approve_by_call_id_after_pending(self) -> None:
        from infrastructure.memory.in_memory_memory import InMemoryMemory

        tool = FakeTool()
        policy = ToolPolicy().with_permission(ToolPermission("swap_music", ToolRiskLevel.HIGH))
        memory = InMemoryMemory()
        executor = ToolExecutor(tools={"swap_music": tool}, tool_policy=policy, memory=memory)

        # "Request A" -- LLM yeu cau goi tool rui ro cao
        pending = await executor.execute(_call())
        assert pending.status == ToolExecutionStatus.PENDING_APPROVAL
        assert tool.call_count == 0

        # "Request B" -- hoan toan doc lap, CHI co call_id (giong nhu
        # Backend nhan duoc tu request duyet cua nguoi dung)
        call_id = pending.tool_call.call_id
        outcome = await executor.approve(call_id)

        assert outcome.status == ToolExecutionStatus.EXECUTED
        assert tool.call_count == 1

    async def test_approve_unknown_call_id_returns_not_found(self) -> None:
        from infrastructure.memory.in_memory_memory import InMemoryMemory

        executor = ToolExecutor(tools={}, tool_policy=ToolPolicy(), memory=InMemoryMemory())

        outcome = await executor.approve("call-id-khong-ton-tai")

        assert outcome.status == ToolExecutionStatus.NOT_FOUND

    async def test_approve_removes_pending_action_after_execution(self) -> None:
        from infrastructure.memory.in_memory_memory import InMemoryMemory

        tool = FakeTool()
        policy = ToolPolicy().with_permission(ToolPermission("swap_music", ToolRiskLevel.HIGH))
        memory = InMemoryMemory()
        executor = ToolExecutor(tools={"swap_music": tool}, tool_policy=policy, memory=memory)

        pending = await executor.execute(_call())
        call_id = pending.tool_call.call_id
        await executor.approve(call_id)

        # Duyet lan hai voi cung call_id -> phai NOT_FOUND, khong duoc
        # thuc thi lai lan nua (tranh double-execute).
        second_attempt = await executor.approve(call_id)
        assert second_attempt.status == ToolExecutionStatus.NOT_FOUND
        assert tool.call_count == 1  # van chi 1 lan