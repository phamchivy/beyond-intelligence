"""
Unit test cho bootstrap/container.py -- dung Settings voi provider=mock,
khong goi mang, xac nhan container lap rap dung Agent/DecisionService
tu cau hinh (khong hardcode gia tri o container).
"""
from __future__ import annotations

from application.agent.agent import Agent
from application.services.decision_service import DecisionService
from bootstrap.container import build_agent_from_settings, build_decision_service
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