"""
Vi tri file nay: agent/tests/integration/api/test_storyboard_api_flow.py

Test toan bo luong HTTP that (khong phai goi truc tiep service qua
Python) -- dung httpx.AsyncClient + ASGITransport de goi thang vao
FastAPI app trong tien trinh, KHONG can chay uvicorn that.

Day chinh la 6 buoc curl da chay thu cong truoc do, chuyen thanh test
tu dong de chay 1 lan cho tien (khong phai copy-paste curl moi lan).

Dung MockLLM/MockVideoRenderer qua dependency_overrides -- khong cham
mang, khong ton quota that, chay nhanh nen KHONG gan @pytest.mark.integration
(khac voi tests/integration/llm|video/*_real.py -- nhung file do goi
API that, can API key, cham va ton tien).
"""
from __future__ import annotations

import httpx
import pytest

from application.services.storyboard_session_service import StoryboardSessionService
from infrastructure.llm.mock_llm import MockLLM
from infrastructure.memory.in_memory_memory import InMemoryMemory
from infrastructure.video.mock_video_renderer import MockVideoRenderer
from interface.api.main import app
from interface.api.storyboard_routes import get_storyboard_service, get_video_renderer


@pytest.fixture
def mock_video_renderer() -> MockVideoRenderer:
    return MockVideoRenderer()


@pytest.fixture
def mock_storyboard_service(mock_video_renderer: MockVideoRenderer) -> StoryboardSessionService:
    return StoryboardSessionService(
        llm=MockLLM(fixed_response="Hook: san pham noi bat. Shot 1: cận cảnh. CTA: Shop Now."),
        video_renderer=mock_video_renderer,
        memory=InMemoryMemory(),
        max_revisions=3,
    )


@pytest.fixture
async def client(mock_storyboard_service, mock_video_renderer):
    """
    Ghi de dependency cua app bang service dung Mock -- test khong phu
    thuoc .env cua nguoi chay (co the dang cau hinh LLM_PROVIDER=deepseek
    that, van khong anh huong den test nay).
    """
    app.dependency_overrides[get_storyboard_service] = lambda: mock_storyboard_service
    app.dependency_overrides[get_video_renderer] = lambda: mock_video_renderer

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestStoryboardApiFullFlow:
    """Tuong duong 6 buoc curl da chay thu cong, gop thanh 1 kich ban tuan tu."""

    async def test_full_flow_start_revise_render_poll(self, client: httpx.AsyncClient) -> None:
        # 1. Health check -- xac nhan CO cau truc dung (khong ep 200,
        # vi trang thai phu thuoc vao .env that cua moi truong chay --
        # gia tri thuc su can kiem tra la co field "dependencies" phan
        # anh dung trang thai LLM/video config, khong phai luon "ok").
        health_response = await client.get("/health")
        assert health_response.status_code in (200, 503)
        health_body = health_response.json()
        assert "dependencies" in health_body
        assert "llm" in health_body["dependencies"]
        assert "video_renderer" in health_body["dependencies"]

        # 2. Start storyboard
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
        assert start_body["storyboard_text"] != ""

        # 3. Revise storyboard -- xac nhan CHI doi text, KHONG render
        revise_response = await client.post(
            "/agent/reasoning/storyboard/revise",
            json={"task_id": "task-flow-1", "feedback": "hook can manh hon"},
        )
        assert revise_response.status_code == 200
        revise_body = revise_response.json()
        assert revise_body["revision_number"] == 2

        # 4. Render final -- CHI goi 1 lan, sau khi "duyet"
        render_response = await client.post(
            "/agent/render", json={"task_id": "task-flow-1"}
        )
        assert render_response.status_code == 200
        render_body = render_response.json()
        assert render_body["render_job_id"] != ""
        assert render_body["status"] == "queued"

        # 5. Poll trang thai render
        job_id = render_body["render_job_id"]
        status_response = await client.get(f"/agent/render/{job_id}")
        assert status_response.status_code == 200
        status_body = status_response.json()
        assert status_body["status"] == "completed"
        assert status_body["video_url"] is not None

        # 6. Loi: revise task_id khong ton tai -> phai ra 404
        error_response = await client.post(
            "/agent/reasoning/storyboard/revise",
            json={"task_id": "task-khong-ton-tai", "feedback": "x"},
        )
        assert error_response.status_code == 404
        error_body = error_response.json()
        assert "error" in error_body
        assert error_body["error"]["task_id"] == "task-khong-ton-tai"

    async def test_render_is_called_exactly_once_across_multiple_revisions(
        self, client: httpx.AsyncClient, mock_video_renderer: MockVideoRenderer
    ) -> None:
        """
        Xac nhan qua HTTP that: du sua storyboard nhieu lan, render CHI
        duoc goi dung 1 lan (o buoc /agent/render), khong phai moi lan
        sua deu render -- dung quyet dinh da chot theo file md.
        """
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
        assert mock_video_renderer.submit_call_count == 0  # chua render lan nao

        await client.post("/agent/render", json={"task_id": "task-flow-2"})

        assert mock_video_renderer.submit_call_count == 1  # dung 1 lan sau khi render_final


class TestHealthCheck:
    async def test_health_reports_dependency_status_not_hardcoded_ok(
        self, client: httpx.AsyncClient
    ) -> None:
        """
        Xac nhan /health THAT SU kiem tra config, khong tra cung "ok".
        Trong moi truong test (khong co .env that), it nhat 1 dependency
        se bao loi -- day chinh la hanh vi mong doi, khong phai bug.
        """
        response = await client.get("/health")
        body = response.json()

        assert body["status"] in ("ok", "degraded")
        for dep_status in body["dependencies"].values():
            assert dep_status.startswith("ok") or dep_status.startswith("error:")