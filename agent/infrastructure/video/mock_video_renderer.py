"""
MockVideoRenderer -- implementation gia cua VideoRenderer port, khong
goi mang, dung de:
  - Unit test use_case render_video (business layer) ma khong can
    Seedance that (tiet kiem tien/thoi gian, khong phu thuoc mang).
  - Mo phong dung tinh chat BAT DONG BO: submit() tra ve job o trang
    thai QUEUED/PROCESSING ngay, get_status() co the tra ve trang thai
    khac nhau qua nhieu lan goi (mo phong qua trinh xu ly that).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count

from domain.ports.video_renderer import RenderJob, RenderJobStatus, RenderRequest


@dataclass
class MockVideoRenderer:
    """
    VideoRenderer gia.

    `status_sequence`: danh sach trang thai se tra ve theo THU TU moi
    lan get_status() duoc goi cho CUNG mot job_id -- mo phong qua trinh
    QUEUED -> PROCESSING -> COMPLETED qua nhieu lan poll. Mac dinh tra
    ve COMPLETED ngay lan dau neu khong cau hinh gi.
    """

    status_sequence: list[RenderJobStatus] = field(
        default_factory=lambda: [RenderJobStatus.COMPLETED]
    )
    final_video_url: str = "https://mock-cdn.test/video/fake.mp4"
    fail_with_error: str | None = None

    _job_ids: "count" = field(default_factory=lambda: count(1), init=False)
    _poll_counts: dict[str, int] = field(default_factory=dict, init=False)
    submit_call_count: int = field(default=0, init=False)

    async def submit(self, request: RenderRequest) -> RenderJob:
        self.submit_call_count += 1
        job_id = f"mock-job-{next(self._job_ids)}"
        self._poll_counts[job_id] = 0
        return RenderJob(job_id=job_id, status=RenderJobStatus.QUEUED)

    async def get_status(self, job_id: str) -> RenderJob:
        poll_index = self._poll_counts.get(job_id, 0)
        self._poll_counts[job_id] = poll_index + 1

        # Qua so lan cau hinh trong status_sequence -> giu nguyen trang
        # thai cuoi cung (thuong la COMPLETED/FAILED).
        index = min(poll_index, len(self.status_sequence) - 1)
        status = self.status_sequence[index]

        if status == RenderJobStatus.FAILED:
            return RenderJob(
                job_id=job_id,
                status=status,
                error=self.fail_with_error or "loi gia lap tu MockVideoRenderer",
            )
        if status == RenderJobStatus.COMPLETED:
            return RenderJob(job_id=job_id, status=status, video_url=self.final_video_url)
        return RenderJob(job_id=job_id, status=status)