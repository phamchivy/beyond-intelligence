"""
Evaluator Port -- "hop dong" cho kha nang danh gia chat luong cua mot
Decision hoac ket qua thuc thi. Khac voi software test thong thuong
(expected == actual), o day la quality >= threshold.

Voi pipeline "... -> Simulate Outcome -> Recommend Action -> Execute ->
Measure Result", Evaluator la thanh phan dung o hai cho:
  1. Truoc khi Execute: cham diem chat luong Decision (co du tin cay
     va bang chung de hanh dong khong).
  2. Sau khi Execute (Measure Result): so sanh ket qua du kien tu
     Simulation voi ket qua thuc te, tra ve EvaluationResult.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from domain.entities.decision import Decision
from domain.value_objects.confidence import Confidence


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Ket qua danh gia mot Decision hoac mot lan thuc thi."""

    score: Confidence  # tai su dung Confidence lam thang diem [0,1] chuan hoa
    passed: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    metrics: dict[str, float] = field(default_factory=dict)  # vd: {"accuracy": 0.9}
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Evaluator(Protocol):
    """
    Port cho kha nang danh gia mot Decision.

    Co nhieu implementation khac nhau: LLM-as-judge, rule-based checker,
    hoac so sanh voi ket qua thuc te (post-hoc evaluation cho buoc
    'Measure Result' trong pipeline).
    """

    async def evaluate(
        self, decision: Decision, context: dict[str, Any] | None = None
    ) -> EvaluationResult:
        ...