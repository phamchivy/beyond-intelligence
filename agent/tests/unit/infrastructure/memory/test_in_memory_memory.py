"""Unit test cho InMemoryMemory -- xac nhan dung contract cua Memory port."""
from __future__ import annotations

from domain.ports.memory import Memory, MemoryItem
from infrastructure.memory.in_memory_memory import InMemoryMemory


class TestConformsToPort:
    def test_satisfies_memory_protocol(self) -> None:
        assert isinstance(InMemoryMemory(), Memory)


class TestSaveAndGet:
    async def test_get_missing_key_returns_none(self) -> None:
        memory = InMemoryMemory()
        assert await memory.get("khong-ton-tai") is None

    async def test_save_then_get_returns_same_item(self) -> None:
        memory = InMemoryMemory()
        item = MemoryItem(key="k1", value={"data": 123})

        await memory.save(item)
        result = await memory.get("k1")

        assert result is not None
        assert result.value == {"data": 123}

    async def test_namespaces_are_isolated(self) -> None:
        memory = InMemoryMemory()
        await memory.save(MemoryItem(key="same-key", value="A", namespace="ns1"))
        await memory.save(MemoryItem(key="same-key", value="B", namespace="ns2"))

        result_ns1 = await memory.get("same-key", namespace="ns1")
        result_ns2 = await memory.get("same-key", namespace="ns2")

        assert result_ns1.value == "A"
        assert result_ns2.value == "B"


class TestDelete:
    async def test_delete_removes_item(self) -> None:
        memory = InMemoryMemory()
        await memory.save(MemoryItem(key="k1", value="x"))

        await memory.delete("k1")

        assert await memory.get("k1") is None

    async def test_delete_missing_key_does_not_raise(self) -> None:
        memory = InMemoryMemory()
        await memory.delete("khong-ton-tai")  # khong duoc raise loi


class TestListKeys:
    async def test_lists_only_keys_in_given_namespace(self) -> None:
        memory = InMemoryMemory()
        await memory.save(MemoryItem(key="a", value=1, namespace="ns1"))
        await memory.save(MemoryItem(key="b", value=2, namespace="ns1"))
        await memory.save(MemoryItem(key="c", value=3, namespace="ns2"))

        keys = await memory.list_keys(namespace="ns1")

        assert sorted(keys) == ["a", "b"]