"""Unit test cho InMemoryRetriever -- xep hang bang keyword overlap."""
from __future__ import annotations

from domain.entities.context import RetrievedDocument
from domain.ports.retriever import Retriever
from infrastructure.retrieval.in_memory_retriever import InMemoryRetriever


class TestConformsToPort:
    def test_satisfies_retriever_protocol(self) -> None:
        assert isinstance(InMemoryRetriever(documents=[]), Retriever)


class TestRetrieve:
    async def test_returns_documents_matching_query_terms(self) -> None:
        docs = [
            RetrievedDocument(content="video ban giay the thao chuyen doi tot", source="v1", score=0.0),
            RetrievedDocument(content="video ban ao thun mua he", source="v2", score=0.0),
            RetrievedDocument(content="khong lien quan gi ca", source="v3", score=0.0),
        ]
        retriever = InMemoryRetriever(documents=docs)

        results = await retriever.retrieve("video ban giay the thao", top_k=5)

        assert len(results) >= 1
        assert results[0].source == "v1"  # trung nhieu tu khoa nhat

    async def test_ranks_by_overlap_score_descending(self) -> None:
        docs = [
            RetrievedDocument(content="a b c d", source="high", score=0.0),
            RetrievedDocument(content="a x y z", source="low", score=0.0),
        ]
        retriever = InMemoryRetriever(documents=docs)

        results = await retriever.retrieve("a b c", top_k=5)

        assert results[0].source == "high"
        assert results[0].score > results[1].score

    async def test_excludes_documents_with_zero_overlap(self) -> None:
        docs = [RetrievedDocument(content="san pham giay dep thoi trang", source="v1", score=0.0)]
        retriever = InMemoryRetriever(documents=docs)

        results = await retriever.retrieve("cong thuc nau an mon chay", top_k=5)

        assert results == []

    async def test_respects_top_k_limit(self) -> None:
        docs = [
            RetrievedDocument(content="tu khoa chung", source=f"v{i}", score=0.0) for i in range(10)
        ]
        retriever = InMemoryRetriever(documents=docs)

        results = await retriever.retrieve("tu khoa chung", top_k=3)

        assert len(results) == 3

    async def test_empty_query_returns_empty_list(self) -> None:
        docs = [RetrievedDocument(content="bat ky noi dung gi", source="v1", score=0.0)]
        retriever = InMemoryRetriever(documents=docs)

        results = await retriever.retrieve("", top_k=5)

        assert results == []