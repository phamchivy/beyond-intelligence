"""
Unit test cho:
  1. MockVideoRenderer -- xac nhan khop dung Protocol VideoRenderer, mo
     phong dung tinh chat bat dong bo (QUEUED -> PROCESSING -> COMPLETED).
  2. LLMMessage/ImagePart moi mo rong -- xac nhan tuong thich nguoc
     (message chi text van tao duoc binh thuong, khong bat buoc truyen
     images).
"""
from __future__ import annotations

from domain.ports.llm import ImagePart, LLMMessage, MessageRole
from domain.ports.video_renderer import (
    ReferenceImage,
    RenderJobStatus,
    RenderRequest,
    VideoRenderer,
)
from infrastructure.video.mock_video_renderer import MockVideoRenderer


class TestConformsToPort:
    def test_mock_video_renderer_satisfies_protocol(self) -> None:
        assert isinstance(MockVideoRenderer(), VideoRenderer)


class TestSubmit:
    async def test_submit_returns_job_with_id(self) -> None:
        renderer = MockVideoRenderer()
        request = RenderRequest(prompt="san pham xoay 360 do tren nen trang")

        job = await renderer.submit(request)

        assert job.job_id != ""
        assert job.status == RenderJobStatus.QUEUED

    async def test_submit_accepts_reference_images(self) -> None:
        renderer = MockVideoRenderer()
        request = RenderRequest(
            prompt="quang cao san pham",
            reference_images=(ReferenceImage(image_bytes=b"fake-bytes", role="product"),),
        )

        job = await renderer.submit(request)

        assert job.status == RenderJobStatus.QUEUED
        assert renderer.submit_call_count == 1


class TestGetStatusPolling:
    async def test_default_returns_completed_immediately(self) -> None:
        renderer = MockVideoRenderer()
        job = await renderer.submit(RenderRequest(prompt="x"))

        status = await renderer.get_status(job.job_id)

        assert status.status == RenderJobStatus.COMPLETED
        assert status.video_url is not None

    async def test_simulates_progression_across_multiple_polls(self) -> None:
        renderer = MockVideoRenderer(
            status_sequence=[
                RenderJobStatus.QUEUED,
                RenderJobStatus.PROCESSING,
                RenderJobStatus.COMPLETED,
            ]
        )
        job = await renderer.submit(RenderRequest(prompt="x"))

        first = await renderer.get_status(job.job_id)
        second = await renderer.get_status(job.job_id)
        third = await renderer.get_status(job.job_id)
        fourth = await renderer.get_status(job.job_id)  # qua het sequence -> giu trang thai cuoi

        assert [first.status, second.status, third.status, fourth.status] == [
            RenderJobStatus.QUEUED,
            RenderJobStatus.PROCESSING,
            RenderJobStatus.COMPLETED,
            RenderJobStatus.COMPLETED,
        ]

    async def test_simulates_failure(self) -> None:
        renderer = MockVideoRenderer(
            status_sequence=[RenderJobStatus.FAILED], fail_with_error="video vuot qua do dai toi da"
        )
        job = await renderer.submit(RenderRequest(prompt="x"))

        status = await renderer.get_status(job.job_id)

        assert status.status == RenderJobStatus.FAILED
        assert status.error == "video vuot qua do dai toi da"

    async def test_different_jobs_have_independent_poll_state(self) -> None:
        renderer = MockVideoRenderer(
            status_sequence=[RenderJobStatus.QUEUED, RenderJobStatus.COMPLETED]
        )
        job_a = await renderer.submit(RenderRequest(prompt="a"))
        job_b = await renderer.submit(RenderRequest(prompt="b"))

        status_a_first = await renderer.get_status(job_a.job_id)
        status_b_first = await renderer.get_status(job_b.job_id)

        # Ca hai deu o lan poll DAU TIEN cua rieng minh -> deu QUEUED,
        # khong bi anh huong lan nhau du dung chung renderer.
        assert status_a_first.status == RenderJobStatus.QUEUED
        assert status_b_first.status == RenderJobStatus.QUEUED


class TestMultimodalLLMMessage:
    def test_text_only_message_still_works_without_images(self) -> None:
        message = LLMMessage(role=MessageRole.USER, content="chao ban")
        assert message.images == ()

    def test_message_can_carry_image_parts(self) -> None:
        image = ImagePart(image_bytes=b"fake-frame-bytes", mime_type="image/jpeg")
        message = LLMMessage(
            role=MessageRole.USER,
            content="So sanh frame nay voi anh san pham goc",
            images=(image,),
        )

        assert len(message.images) == 1
        assert message.images[0].mime_type == "image/jpeg"