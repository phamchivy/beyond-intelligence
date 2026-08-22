"""Test: Agent retrieves and includes all 5 RAG chunks in the LLM prompt."""
from __future__ import annotations

import pytest

from application.agent.agent_factory import build_agent
from application.context.context_builder import ContextBuilder
from domain.entities.context import RetrievedDocument
from domain.entities.task import Task
from domain.ports.retriever import Retriever
from infrastructure.llm.mock_llm import MockLLM


class FakeRetrieverWith5Docs:
    """Mock retriever that returns 5 sample storyboard chunks."""

    async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        """Return top_k trending video chunks (hardcoded 5 for this test)."""
        return [
            RetrievedDocument(
                content="""**Category:** Men's Personal Care | **Revenue:** $5,200 | **Views:** 245,000
**Hook:** "Skip the morning routine chaos - 30 seconds to perfect"
**Style:** "Effortless precision for the busy professional"
**CTA:** "Get Gillette SkinGuard Now"

**Scenes:**
| 0-3s | Split screen: messy bathroom vs clean mirror | "Most shaving routines waste 15 minutes" |
| 3-8s | Close-up of SkinGuard tech | "Precision sensors adjust to your skin in 0.3 seconds" |
| 8-15s | Quick shave demo (side angle) | "30 seconds. That's all you need." |
| 15-22s | Before/after comparison | "Smooth. No cuts. No irritation." |
| 22-29s | Product shot + guy checking mirror | "30-second shave. Professional results." |""",
                source="v1_shaver_demo",
                score=0.94,
                metadata={"title": "Gillette SkinGuard Speed Shave", "product_name": "Gillette SkinGuard"}
            ),
            RetrievedDocument(
                content="""**Category:** Men's Personal Care | **Revenue:** $4,800 | **Views:** 198,000
**Hook:** "Busy schedule? Braun does the work in 40 seconds"
**Style:** "The intelligent shaver for modern professionals"
**CTA:** "Shop Braun Series 9"

**Scenes:**
| 0-5s | Quick montage of morning rush | "Running late again?" |
| 5-12s | Braun device with AI animation | "AI learns your beard pattern in seconds" |
| 12-22s | Shaving demo (front & side) | "One pass. Perfect. Every time." |
| 22-28s | Finished look, office setting | "Ready in 40 seconds" |
| 28-30s | Product + QR code | "Braun Series 9. For the professional you." |""",
                source="v2_braun_routine",
                score=0.87,
                metadata={"title": "Braun Series 9 Time-Saver", "product_name": "Braun Series 9"}
            ),
            RetrievedDocument(
                content="""**Category:** Men's Personal Care | **Revenue:** $3,900 | **Views:** 156,000
**Hook:** "Five-blade precision meets 45-minute battery"
**Style:** "The executive's choice for business-ready grooming"

**Scenes:**
| 0-4s | Executive boardroom setting | "First impression happens in seconds" |
| 4-10s | Panasonic Arc5 close-up | "Five-blade synchronization technology" |
| 10-18s | Shaving demo, multiple angles | "Leaves no stubble. Zero irritation." |
| 18-26s | Polished look, ready for meeting | "Meeting ready in 5 minutes" |""",
                source="v3_panasonic_arc",
                score=0.79,
                metadata={"title": "Panasonic Arc5 Executive Shave", "product_name": "Panasonic Arc5"}
            ),
            RetrievedDocument(
                content="""**Category:** Men's Personal Care | **Revenue:** $3,400 | **Views:** 134,000
**Hook:** "Smart shave that adapts to your beard"
**Style:** "Intelligence meets precision grooming"

**Scenes:**
| 0-6s | Problem: patchy shaving results | "Uneven beard growth? Not anymore" |
| 6-14s | Philips Norelco shaver with sensors lit up | "8 adaptive sensors read your beard" |
| 14-22s | Real-time demo | "Adjusts power 200x per second" |
| 22-28s | Perfect result, confident look | "Perfect every single time" |""",
                source="v4_philips_norelco",
                score=0.72,
                metadata={"title": "Philips Norelco S9000 Premium", "product_name": "Philips Norelco S9000"}
            ),
            RetrievedDocument(
                content="""**Category:** Men's Personal Care | **Revenue:** $2,800 | **Views:** 98,000
**Hook:** "Barber quality. Home price. 60-second trim"
**Style:** "Professional grooming without the salon cost"

**Scenes:**
| 0-4s | Quick split: expensive salon vs home | "Skip the $40 barber appointment" |
| 4-12s | Remington F5 detailed shots | "Precision cutting guide. 18 settings." |
| 12-20s | DIY demo: actual haircut | "Barber precision in 60 seconds" |
| 20-28s | Final result: salon-quality cut | "$199 investment. Unlimited cuts." |""",
                source="v5_remington_pro",
                score=0.68,
                metadata={"title": "Remington F5 Professional Cut", "product_name": "Remington F5"}
            ),
        ]


class TestAgentRetrievesAllRAGChunks:
    """Verify agent retrieves and includes all 5 RAG chunks in prompt."""

    @pytest.mark.asyncio
    async def test_agent_includes_all_5_chunks_in_prompt(self):
        """End-to-end: Agent task → ContextBuilder → Retriever → LLM prompt."""

        # Build agent with RAG-enabled ContextBuilder
        retriever = FakeRetrieverWith5Docs()
        context_builder = ContextBuilder(retriever=retriever, top_k=5)

        llm = MockLLM()
        agent = build_agent(
            llm=llm,
            context_builder=context_builder,
            system_prompt="You are a creative director specializing in short-form video.",
            max_iterations=1,  # Just one iteration for this test
        )

        # Run agent with a task
        task = Task.create(
            goal="Generate a storyboard plan for a 30-second video ad for 'Electric Shaver Pro' "
                 "targeting professional men aged 25-45 with emphasis on time-saving and precision"
        )

        decision = await agent.run(task)

        # Verify decision was made
        assert decision is not None
        assert decision.action is not None

        # Verify LLM received all 5 chunks in the prompt
        # MockLLM records the request it receives
        assert llm.last_request is not None
        messages = llm.last_request.messages

        # Find the reference message (MESSAGE 2)
        ref_messages = [m for m in messages if "Reference trending videos" in m.content]
        assert len(ref_messages) == 1, f"Expected 1 reference message, got {len(ref_messages)}"

        ref_msg = ref_messages[0]

        # Assert: all 5 video sources present
        video_sources = [
            "v1_shaver_demo",
            "v2_braun_routine",
            "v3_panasonic_arc",
            "v4_philips_norelco",
            "v5_remington_pro",
        ]
        for source in video_sources:
            assert source in ref_msg.content, \
                f"Video source '{source}' not found in reference message"

        # Assert: all 5 hooks present
        hooks = [
            "Skip the morning routine chaos",
            "Busy schedule? Braun does the work",
            "Five-blade precision meets 45-minute battery",
            "Smart shave that adapts to your beard",
            "Barber quality. Home price. 60-second trim",
        ]
        for hook in hooks:
            assert hook in ref_msg.content, \
                f"Hook '{hook}' not found in reference message"

        # Assert: all 5 product names present
        products = [
            "Gillette SkinGuard",
            "Braun Series 9",
            "Panasonic Arc5",
            "Philips Norelco S9000",
            "Remington F5",
        ]
        for product in products:
            assert product in ref_msg.content, \
                f"Product '{product}' not found in reference message"

    @pytest.mark.asyncio
    async def test_agent_with_empty_retriever_still_works(self):
        """Verify graceful degradation: empty retriever doesn't break agent."""

        # Retriever with no results
        class EmptyRetriever:
            async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
                return []

        retriever = EmptyRetriever()
        context_builder = ContextBuilder(retriever=retriever, top_k=5)

        llm = MockLLM()
        agent = build_agent(
            llm=llm,
            context_builder=context_builder,
            system_prompt="You are helpful.",
            max_iterations=1,
        )

        task = Task.create(goal="Generate something")
        decision = await agent.run(task)

        # Should still work (no crash)
        assert decision is not None

        # Reference message should NOT be present (no docs)
        messages = llm.last_request.messages
        ref_messages = [m for m in messages if "Reference trending videos" in m.content]
        assert len(ref_messages) == 0, "Should not include reference message when no docs"

    @pytest.mark.asyncio
    async def test_agent_with_no_retriever_still_works(self):
        """Verify graceful degradation: no retriever configured at all."""

        # No retriever (None) → ContextBuilder still works, returns empty Context
        context_builder = ContextBuilder(retriever=None, top_k=5)

        llm = MockLLM()
        agent = build_agent(
            llm=llm,
            context_builder=context_builder,
            system_prompt="You are helpful.",
            max_iterations=1,
        )

        task = Task.create(goal="Generate something")
        decision = await agent.run(task)

        # Should still work
        assert decision is not None

        # Reference message should NOT be present
        messages = llm.last_request.messages
        ref_messages = [m for m in messages if "Reference trending videos" in m.content]
        assert len(ref_messages) == 0

    @pytest.mark.asyncio
    async def test_message_order_in_prompt(self):
        """Verify message order: system → reference_docs → goal."""

        retriever = FakeRetrieverWith5Docs()
        context_builder = ContextBuilder(retriever=retriever, top_k=5)

        llm = MockLLM()
        system_prompt = "You are a creative director."
        agent = build_agent(
            llm=llm,
            context_builder=context_builder,
            system_prompt=system_prompt,
            max_iterations=1,
        )

        task = Task.create(goal="Generate storyboard")
        await agent.run(task)

        messages = llm.last_request.messages

        # Message 1: System prompt
        assert system_prompt in messages[0].content

        # Message 2: Reference docs
        assert "Reference trending videos" in messages[1].content

        # Message 3: User goal
        assert "Generate storyboard" in messages[2].content

    @pytest.mark.asyncio
    async def test_all_5_chunks_counted(self):
        """Count occurrences of storyboard markers in prompt."""

        retriever = FakeRetrieverWith5Docs()
        context_builder = ContextBuilder(retriever=retriever, top_k=5)

        llm = MockLLM()
        agent = build_agent(
            llm=llm,
            context_builder=context_builder,
            max_iterations=1,
        )

        task = Task.create(goal="Generate storyboard")
        await agent.run(task)

        messages = llm.last_request.messages
        ref_msg = [m for m in messages if "Reference trending videos" in m.content][0]

        # Count scene markers (each storyboard has multiple scenes)
        scene_count = ref_msg.content.count("| ")  # Markdown table rows
        assert scene_count >= 20, f"Expected at least 20 scene table rows (5 videos × 4 scenes min), got {scene_count}"

        # Count revenue mentions (each storyboard has one)
        revenue_count = ref_msg.content.count("**Revenue:**")
        assert revenue_count == 5, f"Expected 5 revenue entries, got {revenue_count}"

        # Count hook mentions (each storyboard has one)
        hook_count = ref_msg.content.count("**Hook:**")
        assert hook_count == 5, f"Expected 5 hooks, got {hook_count}"
