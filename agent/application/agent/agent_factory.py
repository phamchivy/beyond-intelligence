"""
agent_factory -- ham lap rap mot Agent hoan chinh tu cac dependency da
duoc tao san (LLM, Tool, Policy...).

KHAC voi bootstrap/container.py (Composition Root day du, se code sau):
ham nay KHONG tu doc settings hay tu tao GeminiProvider/MockLLM that --
no chi nhan cac instance da duoc tao san qua tham so, roi lap chung lai
thanh mot Agent. Tach rieng nhu vay de agent_factory co the dung duoc
trong ca test (truyen MockLLM) lan production (container.py truyen
GeminiProvider that) ma khong doi code.
"""
from __future__ import annotations

from application.agent.agent import Agent
from application.context.context_builder import ContextBuilder
from application.execution.executor import ToolExecutor
from application.reasoning.reasoning_service import ReasoningService
from domain.policies.retry_policy import RetryPolicy
from domain.policies.tool_policy import ToolPolicy
from domain.ports.llm import LLM, ToolDefinition
from domain.ports.tool import Tool


def build_agent(
    llm: LLM,
    tools: dict[str, Tool] | None = None,
    tool_definitions: tuple[ToolDefinition, ...] = (),
    retry_policy: RetryPolicy | None = None,
    tool_policy: ToolPolicy | None = None,
    system_prompt: str = "",
    max_iterations: int = 10,
    context_builder: ContextBuilder | None = None,
) -> Agent:
    """
    Lap rap mot Agent tu cac dependency da co.

    Moi tham so co default hop ly cho truong hop don gian (khong Tool,
    dung RetryPolicy/ToolPolicy mac dinh) -- tien loi khi viet test
    nhanh, nhung production nen truyen day du tu settings qua
    bootstrap/container.py.
    """
    reasoning_service = ReasoningService(
        llm=llm,
        retry_policy=retry_policy or RetryPolicy(),
        system_prompt=system_prompt,
    )
    tool_executor = ToolExecutor(
        tools=tools or {},
        tool_policy=tool_policy or ToolPolicy(),
    )

    return Agent(
        reasoning_service=reasoning_service,
        tool_executor=tool_executor,
        available_tools=tool_definitions,
        max_iterations=max_iterations,
        context_builder=context_builder,
    )