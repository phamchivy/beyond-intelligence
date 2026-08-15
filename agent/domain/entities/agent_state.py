"""
AgentState -- trang thai day du cua Agent tai mot buoc xu ly cu the.

Day la entity trung tam nhat trong domain: moi Planner / Executor / Decision
deu doc tu va tra ve AgentState. Bat buoc immutable (frozen=True) de agent
co the "replay" lai toan bo trajectory (chuoi state) phuc vu debug va
evaluation -- neu state bi mutate truc tiep, kha nang time-travel debug
se mat, va ban khong the biet chinh xac state tai step thu N khi co loi.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

from domain.entities.context import Context
from domain.entities.task import Task


class StepStatus(str, Enum):
    """Trang thai cua mot buoc xu ly ben trong Agent (khac voi trang thai cua Task)."""

    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    DONE = "done"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Observation:
    """
    Mot quan sat / ket qua thu duoc sau mot buoc xu ly.

    Vi du: ket qua goi LLM, ket qua tra ve tu mot Tool, du lieu retrieval.
    `source` dung quy uoc dang "loai:ten", vi du "llm:planner" hoac
    "tool:web_search", de sau nay observability co the group/filter theo
    loai nguon ma khong can sua entity.
    """

    step_id: str
    source: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentState:
    """
    Trang thai day du cua mot Agent run tai mot thoi diem.

    State khong tu thay doi -- moi cap nhat di qua cac phuong thuc with_*,
    luon tra ve mot AgentState moi. Agent (application layer) chiu trach
    nhiem gan lai: `state = state.with_observation(obs)`.
    """

    task: Task
    context: Context
    observations: tuple[Observation, ...] = field(default_factory=tuple)
    current_step: int = 0
    status: StepStatus = StepStatus.RUNNING

    def with_observation(self, observation: Observation) -> "AgentState":
        return replace(
            self,
            observations=self.observations + (observation,),
            current_step=self.current_step + 1,
        )

    def with_context(self, context: Context) -> "AgentState":
        return replace(self, context=context)

    def with_status(self, status: StepStatus) -> "AgentState":
        return replace(self, status=status)

    def latest_observation(self) -> Observation | None:
        return self.observations[-1] if self.observations else None