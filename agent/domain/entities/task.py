"""
Task -- dai dien cho mot nhiem vu ma Agent can thuc hien.

Domain entity thuan tuy: khong phu thuoc framework, LLM SDK, DB driver,
config hay logging. Task chi mo ta "la gi", khong biet "lam bang cach nao".
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Task:
    """
    Mot nhiem vu cu the ma Agent duoc giao de thuc hien.

    Task la bat bien (immutable): moi thay doi trang thai phai tra ve
    mot instance Task moi thong qua cac phuong thuc with_*, khong mutate
    truc tiep. Dieu nay cho phep luu lai toan bo lich su thay doi cua
    Task (audit trail) va replay lai khi can debug / evaluate.

    `input_data` va `metadata` la hai truong "mo" (dict tu do) -- day la
    cach entity nay giu duoc tinh tong quat: no khong biet truoc nghiep vu
    cu the can nhung field gi, business layer tu quyet dinh dua gi vao day.
    """

    id: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    input_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        goal: str,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Task":
        """Factory method -- cach chuan de tao Task moi, tu sinh id + timestamp."""
        return Task(
            id=str(uuid4()),
            goal=goal,
            input_data=input_data or {},
            metadata=metadata or {},
        )

    def with_status(self, status: TaskStatus) -> "Task":
        """Tra ve Task moi voi status khac, khong mutate Task hien tai."""
        return replace(self, status=status, updated_at=datetime.now(timezone.utc))

    def is_terminal(self) -> bool:
        """Task da ket thuc (du thanh cong hay that bai) hay chua."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )