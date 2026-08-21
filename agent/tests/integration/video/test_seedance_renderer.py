"""
Vi tri file nay: agent/tests/integration/video/test_seedance_renderer_real.py

Integration test cho SeedanceRenderer -- sinh video THAT qua Seedance
(BytePlus ModelArk). Ton tien that va mat vai chuc giay den vai phut
(sinh video la tac vu bat dong bo).

Tu dong skip neu thieu VIDEO_API_KEY that trong .env.

Chay: pytest tests/integration/ -v -m integration
Luu y: test nay CHAY LAU HON binh thuong (co the toi 3-5 phut) vi phai
poll cho den khi video sinh xong -- neu muon bo qua khi chay nhanh,
dung: pytest tests/integration/ -v -m integration --deselect tests/integration/video/test_seedance_renderer_real.py
"""
from __future__ import annotations

import asyncio

import pytest

from config.settings import VideoRendererSettings
from domain.ports.video_renderer import RenderJobStatus, RenderRequest
from infrastructure.video.seedance_renderer import SeedanceRenderer

pytestmark = pytest.mark.integration

_video_settings = VideoRendererSettings()
_HAS_REAL_API_KEY = _video_settings.api_key is not None

skip_without_api_key = pytest.mark.skipif(
    not _HAS_REAL_API_KEY,
    reason="Can VIDEO_API_KEY that trong .env de chay integration test nay",
)


@pytest.fixture
def seedance_renderer() -> SeedanceRenderer:
    return SeedanceRenderer(config=_video_settings)


async def _poll_until_done(
    renderer: SeedanceRenderer, job_id: str, max_wait_seconds: float = 300.0
):
    """
    Poll get_status() dinh ky cho den khi COMPLETED/FAILED hoac het
    max_wait_seconds -- dung backoff tang dan giong vi du trong tai
    lieu API chinh thuc cua Seedance.
    """
    interval = 5.0
    elapsed = 0.0

    while elapsed < max_wait_seconds:
        job = await renderer.get_status(job_id)
        if job.status in (RenderJobStatus.COMPLETED, RenderJobStatus.FAILED):
            return job
        await asyncio.sleep(interval)
        elapsed += interval
        interval = min(interval * 1.5, 30.0)

    pytest.fail(f"Render job {job_id} khong hoan tat sau {max_wait_seconds}s")


@skip_without_api_key
class TestSeedanceRendererReal:
    async def test_submit_and_poll_until_completed(self, seedance_renderer: SeedanceRenderer) -> None:
        request = RenderRequest(
            prompt=(
                "Photorealistic style: mot chai nuoc suoi dat tren ban go, "
                "anh sang tu nhien, camera zoom nhe vao san pham"
            ),
            aspect_ratio="9:16",
            duration_seconds=4,
        )

        job = await seedance_renderer.submit(request)
        assert job.job_id != ""
        assert job.status == RenderJobStatus.QUEUED

        final_job = await _poll_until_done(seedance_renderer, job.job_id)

        assert final_job.status == RenderJobStatus.COMPLETED
        assert final_job.video_url is not None
        print("\nVIDEO URL:", final_job.video_url)
        assert final_job.video_url.startswith("http")