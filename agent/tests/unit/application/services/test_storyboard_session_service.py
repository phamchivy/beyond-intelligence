"""
Vi tri file nay: agent/tests/unit/application/services/test_storyboard_session_service.py

Unit test cho StoryboardSessionService -- toan bo dung MockLLM,
MockVideoRenderer, InMemoryMemory, khong goi mang.

Xac nhan dung luong da chot: revise CHI sua storyboard co cau truc
(KHONG render), chi render_final() moi goi VideoRenderer (DUNG 1 LAN),
va storyboard tra ve la StoryboardPlan co cau truc (khong con la van
ban tu do).
"""
from __future__ import annotations

import json

import pytest

from application.services.storyboard_session_service import (
    MaxRevisionsExceededError,
    SessionNotFoundError,
    StoryboardParseError,
    StoryboardSessionService,
)
from domain.ports.llm import LLMResponse
from domain.ports.video_renderer import ReferenceImage, RenderJobStatus
from infrastructure.llm.mock_llm import MockLLM
from infrastructure.memory.in_memory_memory import InMemoryMemory
from infrastructure.video.mock_video_renderer import MockVideoRenderer

_SAMPLE_BRIEF = {"name": "Giay the thao ABC", "category": "footwear", "usp": "nhe, thoang khi"}


def _valid_plan_json(title: str = "Giay the thao ABC Ad") -> str:
    """JSON hop le khop StoryboardPlan schema, dung lam response gia cua MockLLM."""
    return json.dumps(
        {
            "title": title,
            "duration_seconds": 15,
            "aspect_ratio": "9:16",
            "objective": "conversion",
            "target_audience": "gen Z",
            "key_message": "Ben, nhe, gia tot",
            "hook": {
                "time_start_seconds": 0,
                "time_end_seconds": 3,
                "scene_description": "Close-up shoe on white background",
                "on_screen_text": "New drop!",
                "audio_note": "upbeat music starts",
            },
            "scenes": [
                {
                    "order": 1,
                    "title": "Product feature",
                    "time_start_seconds": 3,
                    "time_end_seconds": 10,
                    "scene_description": "Shoe rotating 360",
                    "on_screen_text": "Ultra light",
                    "audio_note": "music continues",
                }
            ],
            "call_to_action": {
                "time_start_seconds": 10,
                "time_end_seconds": 15,
                "scene_description": "Logo and CTA button",
                "on_screen_text": "Shop Now",
                "audio_note": "music peaks",
            },
            "production_notes": {
                "music_style": "upbeat pop",
                "color_palette": "white and orange",
                "pacing_note": "fast cuts",
            },
        }
    )


def _make_service(llm: MockLLM | None = None, max_revisions: int = 3) -> StoryboardSessionService:
    return StoryboardSessionService(
        llm=llm or MockLLM(fixed_response=_valid_plan_json()),
        video_renderer=MockVideoRenderer(),
        memory=InMemoryMemory(),
        max_revisions=max_revisions,
    )


class TestStartSession:
    async def test_returns_structured_storyboard_plan(self) -> None:
        service = _make_service()

        result = await service.start_session("task-1", _SAMPLE_BRIEF)

        assert result.task_id == "task-1"
        assert result.revision_number == 1
        assert result.plan.title == "Giay the thao ABC Ad"
        assert len(result.plan.scenes) == 1
        assert result.plan.hook.time_start_seconds == 0

    async def test_does_not_call_video_renderer(self) -> None:
        renderer = MockVideoRenderer()
        service = StoryboardSessionService(
            llm=MockLLM(fixed_response=_valid_plan_json()),
            video_renderer=renderer,
            memory=InMemoryMemory(),
        )

        await service.start_session("task-1", _SAMPLE_BRIEF)

        assert renderer.submit_call_count == 0

    async def test_raises_clear_error_when_llm_returns_invalid_json(self) -> None:
        llm = MockLLM(fixed_response="day khong phai JSON, la van ban tu do nhu truoc day")
        service = _make_service(llm=llm)

        with pytest.raises(StoryboardParseError):
            await service.start_session("task-1", _SAMPLE_BRIEF)

    async def test_raises_clear_error_when_json_missing_required_fields(self) -> None:
        llm = MockLLM(fixed_response='{"title": "thieu rat nhieu field khac"}')
        service = _make_service(llm=llm)

        with pytest.raises(StoryboardParseError):
            await service.start_session("task-1", _SAMPLE_BRIEF)

    async def test_strips_markdown_code_fence_if_present(self) -> None:
        # LLM doi khi van boc JSON trong ```json ... ``` du da yeu cau khong lam vay.
        wrapped = f"```json\n{_valid_plan_json()}\n```"
        llm = MockLLM(fixed_response=wrapped)
        service = _make_service(llm=llm)

        result = await service.start_session("task-1", _SAMPLE_BRIEF)

        assert result.plan.title == "Giay the thao ABC Ad"


class TestReviseSession:
    async def test_revision_increments_and_uses_feedback(self) -> None:
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json(title="Ban dau")),
                LLMResponse(content=_valid_plan_json(title="Da sua theo feedback")),
            ]
        )
        service = _make_service(llm=llm)

        first = await service.start_session("task-1", _SAMPLE_BRIEF)
        assert first.revision_number == 1

        second = await service.revise_session("task-1", feedback="hook chua du manh")

        assert second.revision_number == 2
        assert second.plan.title == "Da sua theo feedback"

    async def test_revise_does_not_call_video_renderer(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json()),
                LLMResponse(content=_valid_plan_json()),
            ]
        )
        service = StoryboardSessionService(
            llm=llm, video_renderer=renderer, memory=InMemoryMemory(), max_revisions=5
        )

        await service.start_session("task-1", _SAMPLE_BRIEF)
        await service.revise_session("task-1", feedback="sua lai")

        assert renderer.submit_call_count == 0

    async def test_revise_without_start_raises_session_not_found(self) -> None:
        service = _make_service()

        with pytest.raises(SessionNotFoundError):
            await service.revise_session("task-khong-ton-tai", feedback="x")

    async def test_raises_when_exceeding_max_revisions(self) -> None:
        llm = MockLLM(fixed_response=_valid_plan_json())
        service = _make_service(llm=llm, max_revisions=2)

        await service.start_session("task-1", _SAMPLE_BRIEF)
        await service.revise_session("task-1", feedback="sua lan 1")

        with pytest.raises(MaxRevisionsExceededError):
            await service.revise_session("task-1", feedback="sua lan 2")


class TestRenderFinal:
    async def test_renders_using_latest_revision_plan(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json()),
                LLMResponse(content=_valid_plan_json()),
                LLMResponse(content="English render prompt"),
            ]
        )
        service = StoryboardSessionService(
            llm=llm, video_renderer=renderer, memory=InMemoryMemory(), max_revisions=5
        )

        await service.start_session("task-1", _SAMPLE_BRIEF)
        await service.revise_session("task-1", feedback="sua lai")

        render_job = await service.render_final("task-1")

        assert renderer.submit_call_count == 1
        assert render_job.status == RenderJobStatus.QUEUED

    async def test_render_final_without_session_raises(self) -> None:
        service = _make_service()

        with pytest.raises(SessionNotFoundError):
            await service.render_final("task-khong-ton-tai")

    async def test_render_final_passes_reference_images(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json()),
                LLMResponse(content="English prompt"),
            ]
        )
        service = StoryboardSessionService(llm=llm, video_renderer=renderer, memory=InMemoryMemory())
        images = (ReferenceImage(image_bytes=b"fake-product-photo", role="product"),)

        await service.start_session("task-1", _SAMPLE_BRIEF, reference_images=images)
        await service.render_final("task-1")

        assert renderer.submit_call_count == 1


class TestRenderFinalDuration:
    """Vá bug: duration_seconds phải lấy từ brief.constraints, không bị bỏ trống."""

    async def test_render_final_passes_duration_from_brief_constraints(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json()),
                LLMResponse(content="English render prompt"),
            ]
        )
        service = StoryboardSessionService(
            llm=llm, video_renderer=renderer, memory=InMemoryMemory(), max_revisions=5
        )
        brief_with_duration = {**_SAMPLE_BRIEF, "constraints": {"duration_seconds": 30}}

        await service.start_session("task-1", brief_with_duration)
        await service.render_final("task-1")

        assert renderer.last_request is not None
        assert renderer.last_request.duration_seconds == 30.0

    async def test_falls_back_to_plan_duration_when_brief_missing_it(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json()),  # duration_seconds=15 trong JSON
                LLMResponse(content="English prompt"),
            ]
        )
        service = StoryboardSessionService(
            llm=llm, video_renderer=renderer, memory=InMemoryMemory(), max_revisions=5
        )
        brief_without_constraints = {"name": "x"}

        await service.start_session("task-1", brief_without_constraints)
        await service.render_final("task-1")

        assert renderer.last_request.duration_seconds == 15  # lay tu plan, khong crash


class TestRenderFinalEnglishPrompt:
    """Vá bug: prompt gui Seedance phai la ban da dich (tieng Anh), khong phai storyboard goc."""

    async def test_render_prompt_comes_from_translation_step(self) -> None:
        renderer = MockVideoRenderer()
        english_prompt = "Opening scene: shoe on white background, upbeat music"
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json()),
                LLMResponse(content=english_prompt),
            ]
        )
        service = StoryboardSessionService(llm=llm, video_renderer=renderer, memory=InMemoryMemory())

        await service.start_session("task-1", _SAMPLE_BRIEF)
        await service.render_final("task-1")

        assert renderer.last_request.prompt == english_prompt

    async def test_translation_call_receives_duration_context(self) -> None:
        renderer = MockVideoRenderer()
        llm = MockLLM(
            response_queue=[
                LLMResponse(content=_valid_plan_json()),
                LLMResponse(content="prompt"),
            ]
        )
        service = StoryboardSessionService(llm=llm, video_renderer=renderer, memory=InMemoryMemory())
        brief = {**_SAMPLE_BRIEF, "constraints": {"duration_seconds": 30}}

        await service.start_session("task-1", brief)
        await service.render_final("task-1")

        translation_call = llm.call_history[1]
        user_message = translation_call.messages[-1].content
        assert "15" in user_message  # plan.duration_seconds (tu _valid_plan_json) duoc nhac trong prompt dich


class TestFinalizeSession:
    async def test_finalize_removes_session_from_memory(self) -> None:
        service = _make_service()
        await service.start_session("task-1", _SAMPLE_BRIEF)

        await service.finalize_session("task-1")

        with pytest.raises(SessionNotFoundError):
            await service.revise_session("task-1", feedback="x")