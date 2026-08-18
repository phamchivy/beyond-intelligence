"""
InMemoryMemory -- implementation dau tien cua Memory port (domain/ports/
memory.py). Luu du lieu trong dict trong tien trinh (process), khong
persist qua restart -- dung cho dev/test/demo, va cho ca production o
quy mo nho (1 instance) truoc khi can PostgresMemory/RedisMemory (them
sau khi ha tang DB duoc chot).

Hoan toan tong quat: khong biet gi ve nghiep vu cu the dang dung no
(pending action, session, cache...) -- chi luu MemoryItem theo key +
namespace dung contract cua Memory port.
"""
from __future__ import annotations

import asyncio

from domain.ports.memory import Memory, MemoryItem


class InMemoryMemory:
    """
    Implementation Memory port bang dict trong bo nho.

    Dung asyncio.Lock de an toan khi nhieu coroutine cung doc/ghi dong
    thoi (vd: nhieu request approve cung luc trong 1 process) -- van
    la single-process, KHONG an toan giua nhieu instance/process khac
    nhau (can RedisMemory/PostgresMemory that cho truong hop do).
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], MemoryItem] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str, namespace: str = "default") -> MemoryItem | None:
        async with self._lock:
            return self._store.get((namespace, key))

    async def save(self, item: MemoryItem) -> None:
        async with self._lock:
            self._store[(item.namespace, item.key)] = item

    async def delete(self, key: str, namespace: str = "default") -> None:
        async with self._lock:
            self._store.pop((namespace, key), None)

    async def list_keys(self, namespace: str = "default") -> list[str]:
        async with self._lock:
            return [k for (ns, k) in self._store.keys() if ns == namespace]