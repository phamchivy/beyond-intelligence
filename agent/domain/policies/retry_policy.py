"""
RetryPolicy -- business rule quyet dinh khi nao nen thu lai (retry) mot
thao tac that bai (vd: goi LLM timeout, Tool execution loi), va cho doi
bao lau truoc khi thu lai.

Tach rieng RetryPolicy khoi ca LLM adapter lan Agent de tranh tinh trang
"retry chong retry" (Agent tu retry x LLM adapter tu retry x HTTP client
tu retry -> mot loi duy nhat co the sinh ra hang chuc request that su
toi Gemini/API). Chi CO MOT noi quyet dinh retry: policy nay. Adapter va
Agent deu phai goi qua day, khong tu viet vong lap retry rieng.
"""
from __future__ import annotations

from dataclasses import dataclass


class RetryableError(Exception):
    """Danh dau mot loi CO THE thu lai (vd: timeout, rate limit, 503)."""


class NonRetryableError(Exception):
    """Danh dau mot loi KHONG nen thu lai (vd: sai tham so, bi tu choi quyen, 400)."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """
    Chien luoc retry theo exponential backoff.

    max_attempts: so lan thu toi da (bao gom lan dau tien).
    base_delay_seconds: do tre truoc lan retry dau tien.
    max_delay_seconds: tran do tre, tranh cho qua lau khi backoff tang cao.
    backoff_multiplier: he so nhan do tre sau moi lan retry that bai.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_multiplier: float = 2.0

    def should_retry(self, attempt: int, error: Exception | None = None) -> bool:
        """
        attempt: so lan DA thu (attempt=1 nghia la lan dau tien vua that bai).

        Neu error la NonRetryableError, luon tra ve False bat ke con
        luot retry hay khong -- vi retry se khong bao gio thanh cong voi
        loai loi nay (vd: sai API key, sai schema tham so).
        """
        if isinstance(error, NonRetryableError):
            return False
        return attempt < self.max_attempts

    def next_delay_seconds(self, attempt: int) -> float:
        """
        Tinh do tre truoc lan retry tiep theo, theo exponential backoff,
        gioi han boi max_delay_seconds.

        attempt=1 -> base_delay_seconds
        attempt=2 -> base_delay_seconds * backoff_multiplier
        attempt=3 -> base_delay_seconds * backoff_multiplier^2
        ...
        """
        delay = self.base_delay_seconds * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)