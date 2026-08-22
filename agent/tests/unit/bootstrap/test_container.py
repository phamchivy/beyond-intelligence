"""
Unit test cho bootstrap/container.py -- dung Settings voi provider=mock,
khong goi mang, xac nhan container lap rap dung Agent/DecisionService
tu cau hinh (khong hardcode gia tri o container).
"""
from __future__ import annotations

from application.agent.agent import Agent
from application.services.decision_service import DecisionService
from bootstrap.container import (
    _build_context_builder,
    _build_retriever,
    _map_trending_videos_response,
    build_agent_from_settings,
    build_decision_service,
)
from config.settings import (
    DecisionPolicySettings,
    LLMProvider,
    LLMSettings,
    RetryPolicySettings,
    Settings,
    ToolPolicySettings,
)
from domain.entities.task import Task
from domain.policies.decision_policy import PolicyOutcome
from infrastructure.retrieval.http_json_retriever import HttpJsonRetriever


def _mock_settings(**overrides) -> Settings:
    """Settings voi provider=mock -- khong can API key, khong cham mang."""
    defaults = dict(
        llm=LLMSettings(provider=LLMProvider.MOCK),
        retry_policy=RetryPolicySettings(max_attempts=2),
        decision_policy=DecisionPolicySettings(auto_execute_threshold=0.8),
        tool_policy=ToolPolicySettings(auto_deny_unknown_tools=True),
        max_iterations=5,
    )
    defaults.update(overrides)
    return Settings(**defaults)


class TestBuildAgentFromSettings:
    def test_returns_agent_instance(self) -> None:
        config = _mock_settings()
        agent = build_agent_from_settings(config=config)

        assert isinstance(agent, Agent)

    async def test_agent_runs_end_to_end_with_mock_llm(self) -> None:
        """
        Test quan trong nhat cua file nay: xac nhan container lap rap
        ra mot Agent THAT SU chay duoc, khong chi dung type-check.
        """
        config = _mock_settings()
        agent = build_agent_from_settings(config=config)

        decision = await agent.run(Task.create(goal="Kiem tra container lap rap dung"))

        assert decision is not None
        assert decision.confidence == 0.7  # gia tri mac dinh hien tai cua Agent

    def test_respects_custom_max_iterations_from_config(self) -> None:
        config = _mock_settings(max_iterations=1)
        agent = build_agent_from_settings(config=config)

        assert agent._max_iterations == 1  # kiem tra gia tri duoc truyen dung tu config


class TestBuildDecisionService:
    def test_returns_decision_service_instance(self) -> None:
        config = _mock_settings()
        service = build_decision_service(config=config)

        assert isinstance(service, DecisionService)

    def test_uses_thresholds_from_config_not_hardcoded(self) -> None:
        # Nguong auto_execute rat thap (0.1) -- neu container hardcode
        # nguong rieng thi test nay se that bai.
        config = _mock_settings(
            decision_policy=DecisionPolicySettings(
                auto_execute_threshold=0.1, reject_threshold=0.05
            )
        )
        service = build_decision_service(config=config)

        from domain.entities.decision import Decision

        decision = Decision(action="x", recommendation="y", confidence=0.2)
        evaluation = service.evaluate(decision)

        assert evaluation.outcome == PolicyOutcome.AUTO_EXECUTE


class TestMapTrendingVideosResponse:
    """Tests for _map_trending_videos_response function."""

    def test_maps_response_items_to_retrieved_documents(self) -> None:
        response_payload = {
            "items": [
                {
                    "id": "chunk1",
                    "video_id": "v1",
                    "text": "Video 1 hook and scenes",
                    "relevance": 0.95,
                    "title": "Product Demo",
                    "product_name": "Widget A",
                },
                {
                    "id": "chunk2",
                    "video_id": "v2",
                    "text": "Video 2 hook and scenes",
                    "relevance": 0.85,
                    "title": "Tutorial",
                    "product_name": "Widget B",
                },
            ]
        }

        docs = _map_trending_videos_response(response_payload)

        assert len(docs) == 2
        assert docs[0].content == "Video 1 hook and scenes"
        assert docs[0].source == "v1"
        assert docs[0].score == 0.95
        assert docs[0].metadata["title"] == "Product Demo"
        assert docs[0].metadata["product_name"] == "Widget A"

        assert docs[1].content == "Video 2 hook and scenes"
        assert docs[1].source == "v2"
        assert docs[1].score == 0.85

    def test_handles_missing_video_id_fallback_to_id(self) -> None:
        response_payload = {
            "items": [
                {
                    "id": "fallback_id",
                    "text": "Hook text",
                    "relevance": 0.9,
                }
            ]
        }

        docs = _map_trending_videos_response(response_payload)

        assert len(docs) == 1
        assert docs[0].source == "fallback_id"

    def test_handles_empty_items_list(self) -> None:
        response_payload = {"items": []}

        docs = _map_trending_videos_response(response_payload)

        assert len(docs) == 0

    def test_handles_missing_items_key(self) -> None:
        response_payload = {}

        docs = _map_trending_videos_response(response_payload)

        assert len(docs) == 0


class TestBuildRetriever:
    """Tests for _build_retriever function."""

    def test_returns_none_when_no_base_url_configured(self) -> None:
        config = _mock_settings(retrieval_base_url=None)

        retriever = _build_retriever(config)

        assert retriever is None

    def test_returns_http_json_retriever_when_base_url_set(self) -> None:
        config = _mock_settings(retrieval_base_url="http://data:8000/api/v1/videos/trending")

        retriever = _build_retriever(config)

        assert isinstance(retriever, HttpJsonRetriever)

    def test_retriever_uses_configured_base_url(self) -> None:
        base_url = "http://data:8000/api/v1/videos/trending"
        config = _mock_settings(retrieval_base_url=base_url)

        retriever = _build_retriever(config)

        assert retriever._base_url == base_url


class TestBuildContextBuilder:
    """Tests for _build_context_builder function."""

    def test_builds_context_builder_with_retriever_when_configured(self) -> None:
        config = _mock_settings(retrieval_base_url="http://data:8000/api/v1/videos/trending")

        builder = _build_context_builder(config)

        assert builder._retriever is not None
        assert isinstance(builder._retriever, HttpJsonRetriever)

    def test_builds_context_builder_with_none_retriever_when_unconfigured(self) -> None:
        config = _mock_settings(retrieval_base_url=None)

        builder = _build_context_builder(config)

        assert builder._retriever is None

    def test_respects_top_k_from_config(self) -> None:
        config = _mock_settings(retrieval_top_k=20, retrieval_base_url=None)

        builder = _build_context_builder(config)

        assert builder._top_k == 20