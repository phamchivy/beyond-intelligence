"""
Unit test cho Agent -- toan bo dung MockLLM/MockTool, khong goi mang.

Muc dich: xac nhan vong lap orchestration chinh (Agent.run) dieu phoi
dung ReasoningService + ToolExecutor, ap dung dung ToolPolicy, va tao
ra Decision hop le tu ket qua cuoi cung.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from application.agent.agent import Agent, MaxIterationsExceededError
from application.agent.agent_factory import build_agent
from application.execution.executor import ToolExecutor
from application.reasoning.reasoning_service import ReasoningService
from domain.entities.task import Task
from domain.policies.retry_policy import RetryPolicy
from domain.policies.tool_policy import ToolPermission, ToolPolicy, ToolRiskLevel
from domain.ports.llm import LLMRequest, LLMResponse, ToolCall, ToolDefinition
from domain.ports.tool import ToolResult
from infrastructure.llm.mock_llm import MockLLM


@dataclass
class FakeTool:
    """Tool gia don gian, ghi lai so lan duoc goi de assert trong test."""

    name: str = "fetch_market_signal"
    description: str = "test tool"
    parameters_schema: dict = field(default_factory=dict)
    call_count: int = field(default=0, init=False)

    async def execute(self, arguments: dict) -> ToolResult:
        self.call_count += 1
        return ToolResult.ok(output="tin hieu thi truong: nhu cau tang 20%")


def _make_agent(llm: MockLLM, tools: dict, tool_policy: ToolPolicy | None = None) -> Agent:
    return build_agent(
        llm=llm,
        tools=tools,
        tool_definitions=(
            ToolDefinition(name="fetch_market_signal", description="lay tin hieu thi truong"),
        ),
        tool_policy=tool_policy,
        retry_policy=RetryPolicy(max_attempts=2),
        max_iterations=5,
    )


class TestAgentSingleStep:
    async def test_returns_decision_when_llm_answers_immediately(self) -> None:
        llm = MockLLM(fixed_response="Nen mo rong sang Singapore")
        agent = _make_agent(llm, tools={})

        decision = await agent.run(Task.create(goal="Phan tich co hoi thi truong"))

        assert decision.recommendation == "Nen mo rong sang Singapore"
        assert decision.confidence == 0.7
        assert llm.call_count == 1


class TestAgentToolLoop:
    async def test_calls_tool_then_produces_final_decision(self) -> None:
        tool = FakeTool()
        tool_policy = ToolPolicy(auto_deny_unknown_tools=True).with_permission(
            ToolPermission("fetch_market_signal", ToolRiskLevel.LOW)
        )

        # Lan goi LLM dau: yeu cau goi tool. Lan hai: tra loi cuoi cung.
        llm = MockLLM(
            response_queue=[
                LLMResponse(
                    content="",
                    tool_calls=(
                        ToolCall(
                            tool_name="fetch_market_signal",
                            arguments={},
                            call_id="call-1",
                        ),
                    ),
                ),
                LLMResponse(content="Dua tren tin hieu thi truong, nen mo rong ngay"),
            ]
        )

        agent = _make_agent(llm, tools={"fetch_market_signal": tool}, tool_policy=tool_policy)
        decision = await agent.run(Task.create(goal="Co nen mo rong thi truong khong?"))

        assert tool.call_count == 1
        assert decision.recommendation == "Dua tren tin hieu thi truong, nen mo rong ngay"
        # Evidence phai chua lai ket qua tool da goi -- dung de truy vet
        assert any("fetch_market_signal" in e for e in decision.evidence)

    async def test_denied_tool_does_not_execute_but_agent_still_continues(self) -> None:
        tool = FakeTool()
        # Khong khai bao permission -> auto_deny_unknown_tools mac dinh True -> DENY
        tool_policy = ToolPolicy(auto_deny_unknown_tools=True)

        llm = MockLLM(
            response_queue=[
                LLMResponse(
                    content="",
                    tool_calls=(
                        ToolCall(tool_name="fetch_market_signal", arguments={}, call_id="c1"),
                    ),
                ),
                LLMResponse(content="Van tra loi duoc du tool bi tu choi"),
            ]
        )

        agent = _make_agent(llm, tools={"fetch_market_signal": tool}, tool_policy=tool_policy)
        decision = await agent.run(Task.create(goal="test"))

        assert tool.call_count == 0  # KHONG duoc thuc thi vi bi DENY
        assert "bi tu choi" in decision.evidence[0]
        assert decision.recommendation == "Van tra loi duoc du tool bi tu choi"


class TestAgentMaxIterations:
    async def test_raises_when_llm_never_gives_final_answer(self) -> None:
        tool = FakeTool()
        tool_policy = ToolPolicy().with_permission(
            ToolPermission("fetch_market_signal", ToolRiskLevel.LOW)
        )
        # LLM luon yeu cau goi tool, khong bao gio tra loi cuoi -> phai
        # dung lai o max_iterations, khong chay vo han.
        always_tool_call = LLMResponse(
            content="",
            tool_calls=(ToolCall(tool_name="fetch_market_signal", arguments={}, call_id="x"),),
        )
        llm = MockLLM(response_queue=[always_tool_call] * 20)

        agent = build_agent(
            llm=llm,
            tools={"fetch_market_signal": tool},
            tool_definitions=(ToolDefinition(name="fetch_market_signal", description="x"),),
            tool_policy=tool_policy,
            max_iterations=3,
        )

        with pytest.raises(MaxIterationsExceededError):
            await agent.run(Task.create(goal="test"))