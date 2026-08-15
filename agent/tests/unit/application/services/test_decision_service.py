"""
Unit test cho DecisionService -- khong can LLM/Tool, chi kiem tra viec
boc DecisionPolicy thanh DecisionEvaluation dung logic.
"""
from __future__ import annotations

from application.services.decision_service import DecisionService
from domain.entities.decision import Decision, Risk
from domain.policies.decision_policy import DecisionPolicy, PolicyOutcome


def _make_service(**policy_kwargs) -> DecisionService:
    return DecisionService(decision_policy=DecisionPolicy(**policy_kwargs))


class TestDecisionServiceEvaluate:
    def test_high_confidence_no_risk_auto_executes(self) -> None:
        service = _make_service()
        decision = Decision(action="expand_market", recommendation="mo rong", confidence=0.9)

        evaluation = service.evaluate(decision)

        assert evaluation.outcome == PolicyOutcome.AUTO_EXECUTE
        assert evaluation.can_execute_now is True
        assert evaluation.decision is decision  # khong bi doi/clone

    def test_high_risk_requires_approval_even_with_high_confidence(self) -> None:
        service = _make_service()
        decision = Decision(
            action="update_price",
            recommendation="giam gia 20%",
            confidence=0.95,
            risks=(Risk("anh huong loi nhuan", "high"),),
        )

        evaluation = service.evaluate(decision)

        assert evaluation.outcome == PolicyOutcome.REQUIRE_APPROVAL
        assert evaluation.can_execute_now is False

    def test_low_confidence_is_rejected(self) -> None:
        service = _make_service()
        decision = Decision(action="expand_market", recommendation="mo rong", confidence=0.1)

        evaluation = service.evaluate(decision)

        assert evaluation.outcome == PolicyOutcome.REJECT

    def test_custom_thresholds_are_respected(self) -> None:
        # Nguong tuy chinh, thap hon mac dinh -- xac nhan DecisionService
        # dung dung DecisionPolicy duoc truyen vao, khong hardcode nguong.
        service = _make_service(auto_execute_threshold=0.5, reject_threshold=0.1)
        decision = Decision(action="test", recommendation="x", confidence=0.6)

        evaluation = service.evaluate(decision)

        assert evaluation.outcome == PolicyOutcome.AUTO_EXECUTE