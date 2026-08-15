"""
DecisionService -- boc DecisionPolicy thanh mot buoc ro rang, tach
biet khoi Agent (Agent chi tao Decision tho tu ket qua reasoning,
KHONG tu quyet dinh co duoc thuc thi hay khong).

Dung dung vi tri "Policy Check" trong Intelligence Pipeline da mo ta
o README.MD goc:

    Decision -> DecisionService (Policy Check) -> Human Approval / Action

Tach rieng khoi Agent de: (1) Agent giu dung nguyen tac "cuc ky mong",
(2) co the doi nguong chinh sach (DecisionPolicy) ma khong dung vao
vong lap reasoning, (3) de test rieng biet, khong can LLM/Tool.
"""
from __future__ import annotations

from dataclasses import dataclass

from domain.entities.decision import Decision
from domain.policies.decision_policy import DecisionPolicy, PolicyOutcome
from observability.logging import get_logger, log_event

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DecisionEvaluation:
    """Ket qua sau khi mot Decision di qua DecisionPolicy."""

    decision: Decision
    outcome: PolicyOutcome

    @property
    def can_execute_now(self) -> bool:
        return self.outcome == PolicyOutcome.AUTO_EXECUTE


class DecisionService:
    """
    Nhan Decision tho tu Agent, ap dung DecisionPolicy, tra ve ket qua
    kem PolicyOutcome de tang tren (Backend/Frontend) biet phai lam gi
    tiep: tu thuc thi (AUTO_EXECUTE), hien Action Card cho nguoi duyet
    (REQUIRE_APPROVAL), hay bao khong du can cu (REJECT).
    """

    def __init__(self, decision_policy: DecisionPolicy) -> None:
        self._decision_policy = decision_policy

    def evaluate(self, decision: Decision) -> DecisionEvaluation:
        outcome = self._decision_policy.evaluate(decision)

        log_event(
            logger,
            "info",
            "decision_evaluated",
            action=decision.action,
            confidence=decision.confidence,
            is_high_risk=decision.is_high_risk(),
            outcome=outcome.value,
        )

        return DecisionEvaluation(decision=decision, outcome=outcome)