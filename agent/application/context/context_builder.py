from __future__ import annotations

from domain.entities.context import Context
from domain.entities.task import Task
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.retriever import Retriever
from observability.logging import get_logger, log_event

logger = get_logger(__name__)


class ContextBuilder:
    def __init__(self, retriever: Retriever | None, top_k: int = 5) -> None:
        self._retriever = retriever
        self._top_k = top_k

    async def build(self, task: Task) -> Context:
        if self._retriever is None:
            return Context()
        try:
            documents = await self._retriever.retrieve(task.goal, top_k=self._top_k)
        except (RetryableError, NonRetryableError) as exc:
            log_event(logger, "warning", "context_retrieval_failed", task_id=task.id, error=str(exc))
            return Context()
        return Context().with_documents(documents)
