"""
TokenUsage -- Value Object dai dien cho luong token da dung trong mot lan
goi LLM, va co the cong don qua nhieu lan goi trong ca pipeline.

Voi kien truc "AI Decision & Execution System" (Market Signal -> Opportunity
-> Analyze -> Strategy -> Simulate -> Execute), mot lan chay co the goi LLM
nhieu lan (moi buoc mot lan, hoac nhieu lan neu co retry/reasoning). TokenUsage
ho tro toan tu `+` de cong don, phuc vu truc tiep cho:
  - Do luong chi phi/hieu nang toan bo pipeline (Technical criteria)
  - Log/trace tong token & uoc tinh cost cho tung Decision (Observability)

Luu y: TokenUsage KHONG tu tinh gia tien (USD) o day, vi don gia
($/token) la config, thay doi theo model/provider/thoi diem -- khong
phai business rule co dinh cua domain. Uoc tinh cost nen duoc tinh o
tang application/infrastructure, dua tren TokenUsage nay + pricing
table lay tu config.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """
    So luong token da dung cho mot lan goi LLM (hoac tong hop nhieu lan goi).

    Value Object: bat bien, so sanh theo gia tri, khong co identity.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0 or self.completion_tokens < 0:
            raise ValueError("Token counts cannot be negative")

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """
        Cong don hai TokenUsage -- dung de tong hop token qua nhieu buoc
        cua pipeline:

            total = TokenUsage()
            for step in pipeline_steps:
                total = total + step.token_usage
        """
        if not isinstance(other, TokenUsage):
            return NotImplemented
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
        )

    @staticmethod
    def total(usages: list["TokenUsage"]) -> "TokenUsage":
        """Cong don mot danh sach TokenUsage -- tien loi hon vong lap thu cong."""
        result = TokenUsage()
        for usage in usages:
            result = result + usage
        return result

    def estimate_cost_usd(self, price_per_1k_prompt: float, price_per_1k_completion: float) -> float:
        """
        Uoc tinh chi phi USD dua tren don gia truyen vao tu ben ngoai
        (config/pricing table theo model), KHONG hardcode gia trong domain.

        Vi du goi tu application layer:
            usage.estimate_cost_usd(
                settings.pricing[model].prompt_per_1k,
                settings.pricing[model].completion_per_1k,
            )
        """
        return (
            (self.prompt_tokens / 1000) * price_per_1k_prompt
            + (self.completion_tokens / 1000) * price_per_1k_completion
        )