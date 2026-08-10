"""
Decision -- ket qua cuoi cung ma Agent dua ra sau khi reasoning / planning /
execution.

Cau truc bam theo Decision Model da dinh nghia o README du an: moi quyet
dinh AI phai la structured object, co evidence / confidence / risk di kem,
khong phai chuoi text tu do. Dong thoi luu kem prompt_version + model_version
de dam bao truy vet duoc (traceability) -- dung nguyen tac explainable AI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class Risk:
    description: str
    severity: str = "low"  # "low" | "medium" | "high"


@dataclass(frozen=True, slots=True)
class Decision:
    """
    Mot quyet dinh co cau truc do Agent sinh ra.

    `confidence` bi rang buoc trong khoang [0.0, 1.0] ngay tai domain --
    day la business rule cua Decision, khong phai validation cua API layer.
    (Ghi chu: khi code sang value_objects/confidence.py, co the boc
    `confidence: float` thanh Value Object rieng -- Decision se doi kieu
    field nhung logic __post_init__ nay se chuyen vao Value Object do.)
    """

    action: str
    recommendation: str
    confidence: float
    evidence: tuple[str, ...] = field(default_factory=tuple)
    expected_impact: dict[str, float] = field(default_factory=dict)
    risks: tuple[Risk, ...] = field(default_factory=tuple)
    alternatives: tuple[str, ...] = field(default_factory=tuple)

    # Truy vet nguon goc quyet dinh -- bat buoc cho explainability.
    # Day KHONG phai la noi de log -- chi la du lieu duoc gan vao entity.
    # Viec ghi log (observability) do application layer thuc hien khi
    # tao ra Decision nay, xem giai thich ben duoi.
    model_name: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be within [0.0, 1.0], got {self.confidence}"
            )

    def is_high_risk(self) -> bool:
        return any(r.severity == "high" for r in self.risks)

    def requires_human_approval(self, threshold: float = 0.7) -> bool:
        """
        Business rule: quyet dinh can con nguoi phe duyet neu confidence
        thap hon nguong, hoac co rui ro cao -- khop voi luong
        'Human Approval / Policy Check' trong Intelligence Pipeline (README).
        """
        return self.confidence < threshold or self.is_high_risk()