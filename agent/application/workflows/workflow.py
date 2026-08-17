"""
Workflow -- pipeline nhieu buoc TUONG MINH, khac voi vong lap ReAct tu
do cua Agent (application/agent/agent.py).

Dung Workflow khi nghiep vu can mot TRINH TU CO DINH, biet truoc (vd:
"Danh gia rui ro -> Truy xuat lich su -> Sinh de xuat -> Tong hop Decision"),
khong muon de LLM tu quyet dinh buoc tiep theo la gi (nhu Agent lam).
Day chinh la dang pipeline nhieu buoc da mo ta trong tai lieu san pham
(vd: 6 buoc cua luong AdGuard/SentraLoop).

Hoan toan tong quat: Workflow khong biet gi ve tung buoc cu the lam gi
-- moi buoc (WorkflowStep) la mot ham duoc dinh nghia rieng trong
business/domains/<ten_domain>/workflows/, Workflow chi dieu phoi tuan
tu, dung y het tinh than "Agent phai mong" da ap dung cho Agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from domain.entities.agent_state import AgentState
from observability.logging import get_logger, log_duration, log_event

logger = get_logger(__name__)

WorkflowStepFn = Callable[[AgentState], Awaitable[AgentState]]


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """
    Mot buoc trong Workflow.

    `run` nhan AgentState hien tai, tra ve AgentState MOI (cap nhat bat
    bien, dung nguyen tac da ap dung cho AgentState) -- moi buoc thuong
    se ket thuc bang `state.with_observation(...)` de ghi lai ket qua
    cua buoc do truoc khi tra ve.
    """

    name: str
    run: WorkflowStepFn


class Workflow:
    """
    Dieu phoi mot chuoi WorkflowStep co dinh, tuan tu tung buoc mot.

    Khac voi Agent (co the lap lai reasoning nhieu lan tuy LLM quyet
    dinh), Workflow chay dung 1 lan qua tung buoc theo dung thu tu da
    khai bao khi khoi tao -- phu hop khi trinh tu nghiep vu da biet
    truoc va khong can LLM tu dieu huong.
    """

    def __init__(self, steps: list[WorkflowStep]) -> None:
        if not steps:
            raise ValueError("Workflow phai co it nhat mot buoc (WorkflowStep)")
        self._steps = steps

    async def run(self, initial_state: AgentState) -> AgentState:
        state = initial_state
        log_event(
            logger,
            "info",
            "workflow_started",
            task_id=state.task.id,
            step_count=len(self._steps),
            step_names=[s.name for s in self._steps],
        )

        for step in self._steps:
            with log_duration(logger, "workflow_step_completed", step_name=step.name):
                state = await step.run(state)

        log_event(
            logger,
            "info",
            "workflow_completed",
            task_id=state.task.id,
            total_observations=len(state.observations),
        )
        return state