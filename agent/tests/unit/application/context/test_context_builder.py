from __future__ import annotations

from dataclasses import dataclass

import pytest

from application.context.context_builder import ContextBuilder
from domain.entities.context import RetrievedDocument
from domain.entities.task import Task
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.retriever import Retriever


@dataclass
class FakeRetriever:
    """Hand-rolled fake retriever for testing ContextBuilder."""

    documents: list[RetrievedDocument] | None = None
    error: Exception | None = None

    async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        if self.error:
            raise self.error
        return self.documents or []


class TestContextBuilderNoRetriever:
    """Tests for ContextBuilder with retriever=None."""

    @pytest.mark.asyncio
    async def test_returns_empty_context_when_no_retriever(self):
        builder = ContextBuilder(retriever=None)
        task = Task.create(goal="test goal")
        context = await builder.build(task)

        assert context.retrieved_documents == ()


class TestContextBuilderWithDocuments:
    """Tests for ContextBuilder with a successful retriever."""

    @pytest.mark.asyncio
    async def test_returns_context_with_documents(self):
        docs = [
            RetrievedDocument(content="Hook 1", source="v1", score=0.9, metadata={}),
            RetrievedDocument(content="Hook 2", source="v2", score=0.8, metadata={}),
        ]
        retriever = FakeRetriever(documents=docs)
        builder = ContextBuilder(retriever=retriever, top_k=2)
        task = Task.create(goal="test goal")

        context = await builder.build(task)

        assert len(context.retrieved_documents) == 2
        assert context.retrieved_documents[0].content == "Hook 1"
        assert context.retrieved_documents[1].content == "Hook 2"

    @pytest.mark.asyncio
    async def test_passes_query_and_top_k_to_retriever(self):
        """Verify ContextBuilder passes task.goal as query and configured top_k."""
        call_log: list[tuple[str, int]] = []

        class LoggingRetriever:
            async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
                call_log.append((query, top_k))
                return []

        retriever = LoggingRetriever()
        builder = ContextBuilder(retriever=retriever, top_k=10)
        task = Task.create(goal="product name")

        await builder.build(task)

        assert call_log == [("product name", 10)]


class TestContextBuilderGracefulDegradation:
    """Tests for ContextBuilder's error handling."""

    @pytest.mark.asyncio
    async def test_catches_retryable_error_and_returns_empty_context(self):
        retriever = FakeRetriever(error=RetryableError("timeout"))
        builder = ContextBuilder(retriever=retriever)
        task = Task.create(goal="test goal")

        context = await builder.build(task)

        assert context.retrieved_documents == ()

    @pytest.mark.asyncio
    async def test_catches_non_retryable_error_and_returns_empty_context(self):
        retriever = FakeRetriever(error=NonRetryableError("auth failed"))
        builder = ContextBuilder(retriever=retriever)
        task = Task.create(goal="test goal")

        context = await builder.build(task)

        assert context.retrieved_documents == ()
