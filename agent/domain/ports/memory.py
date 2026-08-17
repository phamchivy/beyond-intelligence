"""
Memory Port -- "hop dong" cho kha nang luu tru va truy xuat lai thong tin
qua nhieu lan chay / nhieu buoc cua Agent (khac voi Context, la ngu canh
tuc thoi cho MOT lan reasoning).

Agent chi biet memory.get(...) / memory.save(...), khong biet dang sau
la Redis, PostgreSQL hay in-memory dict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """Mot don vi thong tin duoc luu vao Memory."""

    key: str
    value: Any
    id: str = field(default_factory=lambda: str(uuid4()))
    namespace: str = "default"  # vd: "agent_run:<task_id>", "business:<domain>"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Memory(Protocol):
    """
    Port cho kha nang luu tru/truy xuat MemoryItem theo key.

    `namespace` cho phep tach memory theo boi canh (vd: tach memory cua
    tung task, hoac tach memory theo tung business domain) ma khong can
    doi contract cua port.
    """

    async def get(self, key: str, namespace: str = "default") -> MemoryItem | None:
        ...

    async def save(self, item: MemoryItem) -> None:
        ...

    async def delete(self, key: str, namespace: str = "default") -> None:
        ...

    async def list_keys(self, namespace: str = "default") -> list[str]:
        ...