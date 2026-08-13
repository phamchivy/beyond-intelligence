"""
Confidence -- Value Object dai dien cho do tin cay cua mot ket qua/quyet dinh.

Khac voi Task/AgentState/Decision (co identity, la Entity), Confidence
KHONG co identity: hai Confidence(0.8) o bat ky dau cung "la mot" --
day la dinh nghia chuan cua Value Object trong DDD. Vi vay Confidence
dung __eq__ theo gia tri (dataclass frozen tu sinh san).

Thiet ke rieng cho pipeline nhieu buoc (Market Signal -> Opportunity ->
Strategy -> Simulation -> Decision): moi buoc co the tu sinh ra mot
Confidence, va can mot cach ro rang de ket hop (combine) chung lai
thanh mot Confidence tong the cho quyet dinh cuoi cung.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class ConfidenceLevel(str, Enum):
    """Phan nhom Confidence thanh muc de hien thi/quyet dinh nghiep vu."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Confidence:
    """
    Gia tri do tin cay, luon nam trong [0.0, 1.0].

    Value Object: bat bien, khong co id, so sanh theo gia tri. Dung cho
    ca Decision.confidence lan confidence cua tung buoc trung gian trong
    pipeline (vd: do tin cay cua buoc 'phat hien co hoi thi truong').
    """

    value: float

    # Nguong phan loai muc do tin cay -- co the dieu chinh theo nghiep vu
    # tai noi goi (khong hardcode nguong nghiep vu vao day, day chi la
    # nguong mac dinh hop ly cho phan loai chung). Dung ClassVar de
    # dataclass KHONG coi day la field cua tung instance (Confidence
    # chi co dung mot field du lieu la `value`).
    LOW_THRESHOLD: ClassVar[float] = 0.4
    HIGH_THRESHOLD: ClassVar[float] = 0.75

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(f"Confidence must be within [0.0, 1.0], got {self.value}")

    @property
    def level(self) -> ConfidenceLevel:
        if self.value < self.LOW_THRESHOLD:
            return ConfidenceLevel.LOW
        if self.value < self.HIGH_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.HIGH

    def is_reliable(self, threshold: float = 0.6) -> bool:
        """Confidence co du 'dang tin' de dung lam co so cho buoc tiep theo khong."""
        return self.value >= threshold

    @staticmethod
    def combine(confidences: list["Confidence"], strategy: str = "weakest_link") -> "Confidence":
        """
        Ket hop nhieu Confidence tu nhieu buoc trong pipeline thanh mot
        Confidence tong the.

        strategy:
          - "weakest_link" (mac dinh): lay gia tri nho nhat -- phu hop
            voi pipeline dang chain (Opportunity -> Strategy -> Simulation),
            vi mot buoc yeu se keo thap do tin cay ca chuoi. Day la lua
            chon an toan, phu hop khi Decision cuoi anh huong truc tiep
            den hanh dong thuc te (execute).
          - "average": trung binh cong -- dung khi cac buoc doc lap nhau,
            khong buoc nao "chan" toan bo ket qua.
          - "product": nhan don tung xac suat -- dung khi coi cac buoc
            la cac su kien doc lap can dong thoi dung.

        Neu danh sach rong, tra ve Confidence(0.0) (khong co du lieu =
        khong co can cu de tin).
        """
        if not confidences:
            return Confidence(0.0)

        values = [c.value for c in confidences]

        if strategy == "weakest_link":
            return Confidence(min(values))
        if strategy == "average":
            return Confidence(sum(values) / len(values))
        if strategy == "product":
            result = 1.0
            for v in values:
                result *= v
            return Confidence(result)

        raise ValueError(f"Unknown combine strategy: {strategy}")

    def __lt__(self, other: "Confidence") -> bool:
        return self.value < other.value

    def __le__(self, other: "Confidence") -> bool:
        return self.value <= other.value