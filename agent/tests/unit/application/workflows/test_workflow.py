"""Unit test cho Workflow -- pipeline nhieu buoc co dinh, dung state gia don gian."""
from __future__ import annotations

import pytest

from application.workflows.workflow import Workflow, WorkflowStep
from domain.entities.agent_state import AgentState, Observation
from domain.entities.context import Context
from domain.entities.task import Task


def _initial_state() -> AgentState:
    return AgentState(task=Task.create(goal="test workflow"), context=Context())


async def _step_add_observation(source: str):
    async def _run(state: AgentState) -> AgentState:
        return state.with_observation(
            Observation(step_id=f"step-{state.current_step}", source=source, content="done")
        )

    return _run


class TestWorkflowExecutesInOrder:
    async def test_runs_all_steps_in_declared_order(self) -> None:
        order: list[str] = []

        async def step_a(state: AgentState) -> AgentState:
            order.append("a")
            return state.with_observation(Observation(step_id="1", source="a", content="x"))

        async def step_b(state: AgentState) -> AgentState:
            order.append("b")
            return state.with_observation(Observation(step_id="2", source="b", content="y"))

        workflow = Workflow(
            steps=[WorkflowStep(name="step_a", run=step_a), WorkflowStep(name="step_b", run=step_b)]
        )

        final_state = await workflow.run(_initial_state())

        assert order == ["a", "b"]
        assert len(final_state.observations) == 2
        assert final_state.observations[0].source == "a"
        assert final_state.observations[1].source == "b"

    async def test_state_updates_are_threaded_between_steps(self) -> None:
        # Buoc sau phai nhan duoc state DA duoc cap nhat boi buoc truoc,
        # khong phai state ban dau.
        async def step_check_previous(state: AgentState) -> AgentState:
            assert state.current_step == 1  # da qua 1 buoc truoc do
            return state.with_observation(Observation(step_id="2", source="check", content="ok"))

        async def step_first(state: AgentState) -> AgentState:
            return state.with_observation(Observation(step_id="1", source="first", content="ok"))

        workflow = Workflow(
            steps=[
                WorkflowStep(name="first", run=step_first),
                WorkflowStep(name="check_previous", run=step_check_previous),
            ]
        )

        final_state = await workflow.run(_initial_state())
        assert final_state.current_step == 2


class TestWorkflowValidation:
    def test_raises_when_no_steps_given(self) -> None:
        with pytest.raises(ValueError):
            Workflow(steps=[])