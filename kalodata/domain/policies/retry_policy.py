"""
Vi tri file nay: data/domain/policies/retry_policy.py

Ban rieng cua data/, cung logic nhu agent/domain/policies/retry_policy.py.
"""
from __future__ import annotations

from dataclasses import dataclass


class RetryableError(Exception):
    """Loi CO THE thu lai (vd: timeout, rate limit, 503)."""


class NonRetryableError(Exception):
    """Loi KHONG nen thu lai (vd: sai tham so, bi tu choi quyen, 400)."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_multiplier: float = 2.0

    def should_retry(self, attempt: int, error: Exception | None = None) -> bool:
        if isinstance(error, NonRetryableError):
            return False
        return attempt < self.max_attempts

    def next_delay_seconds(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)