from __future__ import annotations

import pytest

from application.reasoning.reasoning_service import ReasoningService
from domain.entities.agent_state import AgentState
from domain.entities.context import Context, RetrievedDocument
from domain.entities.task import Task
from domain.ports.llm import LLMMessage, MessageRole
from infrastructure.llm.mock_llm import MockLLM


class TestReasoningServiceWithRetrievedDocuments:
    """Tests for ReasoningService._build_request with retrieved documents."""

    def test_includes_retrieved_documents_in_messages(self):
        """Verify that retrieved documents are included as a SYSTEM message."""
        docs = [
            RetrievedDocument(content="Video 1 hook and scenes", source="v1", score=0.9, metadata={}),
            RetrievedDocument(content="Video 2 hook and scenes", source="v2", score=0.8, metadata={}),
        ]
        context = Context().with_documents(docs)
        task = Task.create(goal="generate storyboard for product X")
        state = AgentState(task=task, context=context)

        llm = MockLLM()
        service = ReasoningService(llm=llm, retry_policy=None, system_prompt="")
        request = service._build_request(state, available_tools=())

        # Find the reference message
        messages = request.messages
        ref_messages = [m for m in messages if "Reference trending videos" in m.content]

        assert len(ref_messages) == 1
        ref_msg = ref_messages[0]
        assert ref_msg.role == MessageRole.SYSTEM
        assert "Video 1 hook and scenes" in ref_msg.content
        assert "Video 2 hook and scenes" in ref_msg.content

    def test_reference_message_appears_before_goal(self):
        """Verify that reference docs message appears before the goal USER message."""
        docs = [RetrievedDocument(content="Hook text", source="v1", score=0.9, metadata={})]
        context = Context().with_documents(docs)
        task = Task.create(goal="generate storyboard")
        state = AgentState(task=task, context=context)

        llm = MockLLM()
        service = ReasoningService(llm=llm, retry_policy=None, system_prompt="")
        request = service._build_request(state, available_tools=())

        messages = request.messages
        goal_idx = next(i for i, m in enumerate(messages) if m.content == "generate storyboard")
        ref_idx = next(i for i, m in enumerate(messages) if "Reference trending videos" in m.content)

        assert ref_idx < goal_idx


class TestReasoningServiceEmptyContext:
    """Tests for ReasoningService._build_request with empty context."""

    def test_no_extra_message_when_context_empty(self):
        """Verify that empty context doesn't add extra messages."""
        context = Context()  # empty, no documents
        task = Task.create(goal="generate storyboard")
        state = AgentState(task=task, context=context)

        llm = MockLLM()
        service = ReasoningService(llm=llm, retry_policy=None, system_prompt="")
        request = service._build_request(state, available_tools=())

        messages = request.messages
        # Should contain only: USER message with goal
        assert len(messages) == 1
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "generate storyboard"

    def test_preserves_goal_when_no_documents(self):
        """Verify that task goal is still present when no documents."""
        context = Context()
        task = Task.create(goal="my goal")
        state = AgentState(task=task, context=context)

        llm = MockLLM()
        service = ReasoningService(llm=llm, retry_policy=None, system_prompt="")
        request = service._build_request(state, available_tools=())

        messages = request.messages
        assert any(m.content == "my goal" for m in messages)


class TestReasoningServiceWithSystemPrompt:
    """Tests for ReasoningService._build_request with system prompt."""

    def test_system_prompt_appears_first(self):
        """Verify system prompt is the first message."""
        docs = [RetrievedDocument(content="Hook", source="v1", score=0.9, metadata={})]
        context = Context().with_documents(docs)
        task = Task.create(goal="goal")
        state = AgentState(task=task, context=context)

        llm = MockLLM()
        service = ReasoningService(llm=llm, retry_policy=None, system_prompt="You are helpful")
        request = service._build_request(state, available_tools=())

        assert request.messages[0].role == MessageRole.SYSTEM
        assert request.messages[0].content == "You are helpful"

    def test_message_order_with_all_parts(self):
        """Verify order: system_prompt -> reference_docs -> goal -> observations."""
        docs = [RetrievedDocument(content="Hook", source="v1", score=0.9, metadata={})]
        context = Context().with_documents(docs)
        task = Task.create(goal="my goal")
        state = AgentState(task=task, context=context)

        llm = MockLLM()
        service = ReasoningService(llm=llm, retry_policy=None, system_prompt="System")
        request = service._build_request(state, available_tools=())

        messages = request.messages
        assert messages[0].content == "System"
        assert "Reference trending videos" in messages[1].content
        assert messages[2].content == "my goal"
