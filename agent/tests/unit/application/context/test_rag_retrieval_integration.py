"""Integration test: verify RAG retrieval returns top_k chunks correctly."""
from __future__ import annotations

import pytest

from bootstrap.container import _map_trending_videos_response


class TestRetrievalTopK:
    """Test that retrieval respects top_k configuration."""

    def test_maps_5_items_to_5_documents(self):
        """Verify all 5 items are mapped when top_k=5."""
        # Simulated response from data/api.py with 5 items (like real /api/v1/videos/trending)
        response_payload = {
            "meta": {
                "query": "Electric Shaver Pro time-saving professional",
                "candidates_considered": 143,
                "relevance_gated": False,
            },
            "items": [
                {
                    "id": "chunk_v1",
                    "video_id": "v1_shaver_demo",
                    "title": "Gillette SkinGuard Speed Shave",
                    "url": "https://tiktok.com/@gillette/...",
                    "product_name": "Gillette SkinGuard",
                    "text": "**Hook:** Skip the morning routine chaos\n**Scenes:** [...5 scenes...]",
                    "relevance": 0.94,
                    "revenue_usd": 5200,
                    "views_30d": 245000,
                },
                {
                    "id": "chunk_v2",
                    "video_id": "v2_braun_routine",
                    "title": "Braun Series 9 Time-Saver",
                    "url": "https://tiktok.com/@braun/...",
                    "product_name": "Braun Series 9",
                    "text": "**Hook:** Busy schedule? Braun does the work in 40 seconds\n**Scenes:** [...]",
                    "relevance": 0.87,
                    "revenue_usd": 4800,
                    "views_30d": 198000,
                },
                {
                    "id": "chunk_v3",
                    "video_id": "v3_panasonic_arc",
                    "title": "Panasonic Arc5 Executive Shave",
                    "url": "https://tiktok.com/@panasonic/...",
                    "product_name": "Panasonic Arc5",
                    "text": "**Hook:** Five-blade precision meets 45-minute battery\n**Scenes:** [...]",
                    "relevance": 0.79,
                    "revenue_usd": 3900,
                    "views_30d": 156000,
                },
                {
                    "id": "chunk_v4",
                    "video_id": "v4_philips_norelco",
                    "title": "Philips Norelco S9000 Premium",
                    "url": "https://tiktok.com/@philips/...",
                    "product_name": "Philips Norelco S9000",
                    "text": "**Hook:** Smart shave that adapts to your beard\n**Scenes:** [...]",
                    "relevance": 0.72,
                    "revenue_usd": 3400,
                    "views_30d": 134000,
                },
                {
                    "id": "chunk_v5",
                    "video_id": "v5_remington_pro",
                    "title": "Remington F5 Professional Cut",
                    "url": "https://tiktok.com/@remington/...",
                    "product_name": "Remington F5",
                    "text": "**Hook:** Barber quality. Home price. 60-second trim\n**Scenes:** [...]",
                    "relevance": 0.68,
                    "revenue_usd": 2800,
                    "views_30d": 98000,
                },
            ]
        }

        # Map response to RetrievedDocument list
        docs = _map_trending_videos_response(response_payload)

        # Assert: 5 documents returned
        assert len(docs) == 5, f"Expected 5 documents, got {len(docs)}"

        # Assert: ordered by relevance (descending)
        relevances = [doc.score for doc in docs]
        assert relevances == [0.94, 0.87, 0.79, 0.72, 0.68], \
            f"Documents not in relevance order: {relevances}"

        # Assert: all 5 videos represented
        sources = [doc.source for doc in docs]
        assert sources == [
            "v1_shaver_demo",
            "v2_braun_routine",
            "v3_panasonic_arc",
            "v4_philips_norelco",
            "v5_remington_pro",
        ], f"Unexpected sources: {sources}"

        # Assert: content is populated (not empty)
        for i, doc in enumerate(docs, 1):
            assert len(doc.content) > 0, f"Document {i} has empty content"
            assert "Hook:" in doc.content, f"Document {i} missing Hook in content"
            assert doc.metadata.get("title") is not None, f"Document {i} missing title"
            assert doc.metadata.get("product_name") is not None, f"Document {i} missing product_name"

    def test_handles_fewer_than_top_k_results(self):
        """Verify retrieval gracefully handles when API returns <top_k results."""
        # Sometimes trending index has fewer than 5 videos (e.g., new deployment)
        response_payload = {
            "meta": {"query": "rare product", "candidates_considered": 5},
            "items": [
                {
                    "id": "chunk_1",
                    "video_id": "v1",
                    "title": "Only Video",
                    "text": "Content 1",
                    "relevance": 0.9,
                    "product_name": "Product A",
                },
                {
                    "id": "chunk_2",
                    "video_id": "v2",
                    "title": "Second Video",
                    "text": "Content 2",
                    "relevance": 0.7,
                    "product_name": "Product B",
                },
                # Only 2 results, not 5
            ]
        }

        docs = _map_trending_videos_response(response_payload)

        # Should return 2, not 5 (no padding)
        assert len(docs) == 2
        assert len([d.score for d in docs]) == 2

    def test_empty_response_returns_empty_list(self):
        """Verify retrieval returns empty list when no results."""
        response_payload = {
            "meta": {"query": "gibberish xyz", "candidates_considered": 0},
            "items": []
        }

        docs = _map_trending_videos_response(response_payload)

        assert len(docs) == 0

    def test_all_5_docs_included_in_prompt(self):
        """Verify all 5 retrieved docs are joined into a single prompt message."""
        from application.reasoning.reasoning_service import ReasoningService
        from domain.entities.agent_state import AgentState
        from domain.entities.context import Context, RetrievedDocument
        from domain.entities.task import Task
        from domain.ports.llm import MessageRole
        from infrastructure.llm.mock_llm import MockLLM

        # Build context with 5 documents
        docs = [
            RetrievedDocument(
                content=f"**Storyboard {i}**: Hook and scenes",
                source=f"v{i}",
                score=0.95 - (i * 0.05),
                metadata={"title": f"Video {i}"}
            )
            for i in range(1, 6)  # 5 docs
        ]
        context = Context().with_documents(docs)

        task = Task.create(goal="Generate storyboard")
        state = AgentState(task=task, context=context)

        # Build prompt
        llm = MockLLM()
        service = ReasoningService(llm=llm, retry_policy=None, system_prompt="")
        request = service._build_request(state, available_tools=())

        # Find reference message
        ref_messages = [m for m in request.messages if "Reference trending videos" in m.content]
        assert len(ref_messages) == 1, "Expected exactly 1 reference message"

        ref_msg = ref_messages[0]
        assert ref_msg.role == MessageRole.SYSTEM

        # Assert: all 5 storyboards present
        for i in range(1, 6):
            assert f"**Storyboard {i}**" in ref_msg.content, \
                f"Storyboard {i} missing from prompt"

        # Assert: they're joined with newlines (not separate messages)
        storyboard_count = ref_msg.content.count("**Storyboard")
        assert storyboard_count == 5, \
            f"Expected 5 storyboards in one message, found {storyboard_count}"
