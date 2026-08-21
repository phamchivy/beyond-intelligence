"""
Vi tri file nay: agent/tests/unit/application/services/test_storyboard_session_service.py

Unit test cho StoryboardSessionService -- toan bo dung MockLLM,
MockVideoRenderer, InMemoryMemory, khong goi mang.

Xac nhan dung luong da chot: revise CHI sua text (KHONG render), chi
render_final() moi goi VideoRenderer, va CHI DUNG MOT LAN.
"""
from __future__ import annotations

import pytest

from application.services.storyboard_session_service import (
    MaxRevisionsExceededError,
    SessionNotFoundError,
    StoryboardSessionService,
)
from domain.ports.llm import LLMResponse
from domain.ports.video_renderer import ReferenceImage, RenderJobStatus
from infrastructure.llm.mock_llm import MockLLM
from infrastructure.memory.in_memory_memory import InMemoryMemory
from infrastructure.video.mock_video_renderer import MockVideoRenderer


def _make_service(llm: MockLLM | None = None, max_revisions: int = 3) -> StoryboardSessionService:
    return StoryboardSessionService(
        llm=llm or MockLLM(fixed_response="Hook: ... Shot 1: ... CTA: ..."),
        video_renderer=MockVideoRenderer(),
        memory=InMemoryMemory(),
        max_revisions=max_revisions,
    )


_SAMPLE_BRIEF = {"name": "Giay the thao ABC", "category": "footwear", "usp": "nhe, thoang khi"}


class TestStartSession:
    async def test_returns_storyboard_text_only(self) -> None:
        service = _make_service()

        result = await service.start_session("task-1", _SAMPLE_BRIEF)

        assert result.task_id == "task-1"
        assert result.revision_number == 1
        assert result.storyboard_text != ""

    async def test_does_not_call_video_renderer(self) -> None:
        renderer = MockVideoRenderer()
        service = StoryboardSessionService(
            llm=MockLLM(fixed_response="storyboard text"),
            video_renderer=renderer,
            memory=InMemoryMemory(),
        )

        await service.start_session("task-1", _SAMPLE_BRIEF)

        assert renderer.submit_call_count == 0  # dung luong moi: khong render luc sinh storyboard


class TestReviseSession:
    async def test_revision_increments_and_uses_feedback(self) -> None:
        llm = MockLLM(
            response_queue=[
                LLMResponse(content="storyboard ban dau"),
                LLMResponse(content="storyboard da sua theo feedback"),
            ]
        )
        service = _make_service(llm=llm)

        first = await service.start_session("task-1", _SAMPLE_BRIEF)
        assert first.revision_number == 1

        second = await service.revise_session("task-1", feedback="hook chua du manh")

        assert second.revision_number == 2
        assert second.storyboard_text == "storyboard da sua theo feedback"

    async def test_revise_does_not_call_video_renderer(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[LLMResponse(content="v1"), LLMResponse(content="v2")]
        )
        service = StoryboardSessionService(
            llm=llm, video_renderer=renderer, memory=InMemoryMemory(), max_revisions=5
        )

        await service.start_session("task-1", _SAMPLE_BRIEF)
        await service.revise_session("task-1", feedback="sua lai")

        assert renderer.submit_call_count == 0  # dung luong moi: revise KHONG render

    async def test_revise_without_start_raises_session_not_found(self) -> None:
        service = _make_service()

        with pytest.raises(SessionNotFoundError):
            await service.revise_session("task-khong-ton-tai", feedback="x")

    async def test_raises_when_exceeding_max_revisions(self) -> None:
        llm = MockLLM(fixed_response="storyboard")
        service = _make_service(llm=llm, max_revisions=2)

        await service.start_session("task-1", _SAMPLE_BRIEF)  # revision 1
        await service.revise_session("task-1", feedback="sua lan 1")  # revision 2 -- vua cham max

        with pytest.raises(MaxRevisionsExceededError):
            await service.revise_session("task-1", feedback="sua lan 2")  # vuot qua max


class TestRenderFinal:
    async def test_renders_using_latest_revision_text(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[LLMResponse(content="v1"), LLMResponse(content="v2 da duyet")]
        )
        service = StoryboardSessionService(
            llm=llm, video_renderer=renderer, memory=InMemoryMemory(), max_revisions=5
        )

        await service.start_session("task-1", _SAMPLE_BRIEF)
        await service.revise_session("task-1", feedback="sua lai")

        render_job = await service.render_final("task-1")

        assert renderer.submit_call_count == 1  # CHI goi render dung 1 lan, luc approve
        assert render_job.status == RenderJobStatus.QUEUED

    async def test_render_final_without_session_raises(self) -> None:
        service = _make_service()

        with pytest.raises(SessionNotFoundError):
            await service.render_final("task-khong-ton-tai")

    async def test_render_final_passes_reference_images(self) -> None:
        renderer = MockVideoRenderer()
        service = StoryboardSessionService(
            llm=MockLLM(fixed_response="storyboard"),
            video_renderer=renderer,
            memory=InMemoryMemory(),
        )
        images = (ReferenceImage(image_bytes=b"fake-product-photo", role="product"),)

        await service.start_session("task-1", _SAMPLE_BRIEF, reference_images=images)
        await service.render_final("task-1")

        assert renderer.submit_call_count == 1


class TestFinalizeSession:
    async def test_finalize_removes_session_from_memory(self) -> None:
        service = _make_service()
        await service.start_session("task-1", _SAMPLE_BRIEF)

        await service.finalize_session("task-1")

        with pytest.raises(SessionNotFoundError):
            await service.revise_session("task-1", feedback="x")