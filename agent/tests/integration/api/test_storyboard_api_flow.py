"""
Vi tri file nay: agent/tests/integration/api/test_storyboard_api_flow.py

Test toan bo luong HTTP that (khong phai goi truc tiep service qua
Python) -- dung httpx.AsyncClient + ASGITransport de goi thang vao
FastAPI app trong tien trinh, KHONG can chay uvicorn that.

Dung MockLLM/MockVideoRenderer qua dependency_overrides -- khong cham
mang, khong ton quota that, chay nhanh nen KHONG gan @pytest.mark.integration.
"""
from __future__ import annotations

import json

import httpx
import pytest

from application.services.storyboard_session_service import StoryboardSessionService
from infrastructure.llm.mock_llm import MockLLM
from infrastructure.memory.in_memory_memory import InMemoryMemory
from infrastructure.video.mock_video_renderer import MockVideoRenderer
from interface.api.main import app
from interface.api.storyboard_routes import get_storyboard_service, get_video_renderer


def _valid_plan_json(title: str = "Sample Ad") -> str:
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
                "scene_description": "Close-up product",
                "on_screen_text": "New drop!",
                "audio_note": "music starts",
            },
            "scenes": [
                {
                    "order": 1,
                    "title": "Feature",
                    "time_start_seconds": 3,
                    "time_end_seconds": 10,
                    "scene_description": "Product rotating",
                    "on_screen_text": "Ultra light",
                    "audio_note": "music continues",
                }
            ],
            "call_to_action": {
                "time_start_seconds": 10,
                "time_end_seconds": 15,
                "scene_description": "Logo and CTA",
                "on_screen_text": "Shop Now",
                "audio_note": "music peaks",
            },
            "production_notes": {"music_style": "pop", "color_palette": "white", "pacing_note": "fast"},
        }
    )


@pytest.fixture
def mock_video_renderer() -> MockVideoRenderer:
    return MockVideoRenderer()


@pytest.fixture
def mock_storyboard_service(mock_video_renderer: MockVideoRenderer) -> StoryboardSessionService:
    return StoryboardSessionService(
        llm=MockLLM(fixed_response=_valid_plan_json()),
        video_renderer=mock_video_renderer,
        memory=InMemoryMemory(),
        max_revisions=3,
    )


@pytest.fixture
async def client(mock_storyboard_service, mock_video_renderer):
    app.dependency_overrides[get_storyboard_service] = lambda: mock_storyboard_service
    app.dependency_overrides[get_video_renderer] = lambda: mock_video_renderer

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestStoryboardApiFullFlow:
    async def test_full_flow_start_revise_render_poll(self, client: httpx.AsyncClient) -> None:
        health_response = await client.get("/health")
        assert health_response.status_code in (200, 503)
        health_body = health_response.json()
        assert "dependencies" in health_body

        start_response = await client.post(
            "/agent/reasoning/storyboard",
            json={
                "task_id": "task-flow-1",
                "brief": {"name": "Giay the thao ABC", "usp": "nhe, thoang khi"},
                "reference_assets": [],
            },
        )
        assert start_response.status_code == 200
        start_body = start_response.json()
        assert start_body["task_id"] == "task-flow-1"
        assert start_body["revision_number"] == 1
        assert start_body["plan"]["title"] == "Sample Ad"
        assert len(start_body["plan"]["scenes"]) == 1

        revise_response = await client.post(
            "/agent/reasoning/storyboard/revise",
            json={"task_id": "task-flow-1", "feedback": "hook can manh hon"},
        )
        assert revise_response.status_code == 200
        assert revise_response.json()["revision_number"] == 2

        render_response = await client.post("/agent/render", json={"task_id": "task-flow-1"})
        assert render_response.status_code == 200
        render_body = render_response.json()
        assert render_body["render_job_id"] != ""
        assert render_body["status"] == "queued"

        job_id = render_body["render_job_id"]
        status_response = await client.get(f"/agent/render/{job_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "completed"

        error_response = await client.post(
            "/agent/reasoning/storyboard/revise",
            json={"task_id": "task-khong-ton-tai", "feedback": "x"},
        )
        assert error_response.status_code == 404
        assert "error" in error_response.json()

    async def test_render_is_called_exactly_once_across_multiple_revisions(
        self, client: httpx.AsyncClient, mock_video_renderer: MockVideoRenderer
    ) -> None:
        await client.post(
            "/agent/reasoning/storyboard",
            json={"task_id": "task-flow-2", "brief": {"name": "x"}, "reference_assets": []},
        )
        await client.post(
            "/agent/reasoning/storyboard/revise",
            json={"task_id": "task-flow-2", "feedback": "sua lan 1"},
        )
        await client.post(
            "/agent/reasoning/storyboard/revise",
            json={"task_id": "task-flow-2", "feedback": "sua lan 2"},
        )
        assert mock_video_renderer.submit_call_count == 0

        await client.post("/agent/render", json={"task_id": "task-flow-2"})

        assert mock_video_renderer.submit_call_count == 1


class TestHealthCheck:
    async def test_health_reports_dependency_status_not_hardcoded_ok(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/health")
        body = response.json()

        assert body["status"] in ("ok", "degraded")
        for dep_status in body["dependencies"].values():
            assert dep_status.startswith("ok") or dep_status.startswith("error:")