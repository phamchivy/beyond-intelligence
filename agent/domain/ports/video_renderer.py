"""
VideoRenderer Port -- "hop dong" cho kha nang sinh video tu prompt mo
ta scene/motion + anh tham chieu (product asset that).

Tach RIENG khoi LLM port vi ban chat khac nhau: LLM.generate() la
hoi-dap (text vao, text ra, đong bo, nhanh). VideoRenderer la sinh
media (anh + text vao, video ra, BAT DONG BO -- co the mat vai chuc
giay den vai phut), can co RenderJob + polling, khong the ep vao cung
mot Protocol voi LLM.

Provider cu the (Seedance, hoac provider khac neu doi sau nay) implement
port nay o infrastructure/video/ -- domain/application khong biet ten
Seedance, giong nguyen tac da ap dung cho GeminiProvider voi LLM port.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class RenderJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ReferenceImage:
    """
    Anh tham chieu (thuong la asset san pham that) dung de sinh video --
    provider dung anh nay de dam bao san pham trong video dung asset
    that, khong bi bia hinh (rang buoc bat buoc cua de bai).
    """

    image_bytes: bytes
    mime_type: str = "image/png"
    role: str = "product"  # "product" | "logo" | "style_reference"...


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """Yeu cau sinh mot doan video (thuong ung voi 1 Shot trong StoryboardPlan)."""

    prompt: str
    reference_images: tuple[ReferenceImage, ...] = field(default_factory=tuple)
    duration_seconds: float | None = None
    aspect_ratio: str = "9:16"  # mac dinh dung dinh dang TikTok/Reels theo de bai
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RenderJob:
    """
    Dai dien cho mot yeu cau render dang duoc xu ly bat dong bo.

    `job_id` la thu duy nhat can luu lai (qua Memory port) de sau nay
    poll trang thai -- KHONG can giu nguyen RenderRequest ben minh.
    """

    job_id: str
    status: RenderJobStatus
    video_url: str | None = None
    error: str | None = None


@runtime_checkable
class VideoRenderer(Protocol):
    """
    Port cho kha nang sinh video bat dong bo.

    Quy trinh chuan: submit() -> nhan job_id ngay lap tuc -> poll
    get_status(job_id) dinh ky cho den khi COMPLETED/FAILED. Khong dung
    mot method "generate() cho toi khi xong" duy nhat vi thoi gian sinh
    video co the vuot qua timeout HTTP thong thuong.
    """

    async def submit(self, request: RenderRequest) -> RenderJob:
        ...

    async def get_status(self, job_id: str) -> RenderJob:
        ...