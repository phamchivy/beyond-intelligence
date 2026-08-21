"""
Vi tri file nay: agent/interface/api/storyboard_routes.py

Route HTTP cho storyboard + render -- CUC KY MONG, giong dung nguyen
tac da ap dung cho Agent: khong chua logic nghiep vu, chi dich HTTP
request/response sang goi StoryboardSessionService va nguoc lai.

Video_renderer duoc dung qua service (khong goi truc tiep o day) de
kiem tra trang thai render trong endpoint /agent/render/{job_id}.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException

from application.services.storyboard_session_service import (
    MaxRevisionsExceededError,
    SessionNotFoundError,
    StoryboardSessionService,
)
from bootstrap.container import build_storyboard_session_service, build_video_renderer
from config.settings import settings
from domain.ports.video_renderer import ReferenceImage
from interface.api.schemas import (
    RenderFinalRequest,
    RenderFinalResponse,
    RenderStatusResponse,
    ReviseStoryboardRequest,
    StartStoryboardRequest,
    StoryboardResponse,
)
from observability.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["storyboard"])

# Composition Root chi lap rap luc CO REQUEST DAU TIEN (lazy), KHONG
# phai luc module duoc import -- neu build ngay luc import (eager),
# thieu config/API key hop le se lam CA SERVER khong khoi dong duoc,
# va lam viec test (dependency_overrides) khong the ap dung kip truoc
# khi import that bai. Dung bien module-level + kiem tra None thay vi
# goi truc tiep luc import.
_storyboard_service: StoryboardSessionService | None = None
_video_renderer_instance = None


def get_storyboard_service() -> StoryboardSessionService:
    global _storyboard_service
    if _storyboard_service is None:
        _storyboard_service = build_storyboard_session_service()
    return _storyboard_service


def get_video_renderer():
    global _video_renderer_instance
    if _video_renderer_instance is None:
        _video_renderer_instance = build_video_renderer()
    return _video_renderer_instance


@router.post("/reasoning/storyboard", response_model=StoryboardResponse)
async def start_storyboard(
    request: StartStoryboardRequest,
    service: StoryboardSessionService = Depends(get_storyboard_service),
) -> StoryboardResponse:
    reference_images = tuple(
        ReferenceImage(
            image_bytes=base64.b64decode(asset.content_base64),
            mime_type=asset.mime_type,
            role=asset.asset_role,
        )
        for asset in request.reference_assets
    )

    result = await service.start_session(
        task_id=request.task_id, brief=request.brief, reference_images=reference_images
    )
    return StoryboardResponse(
        task_id=result.task_id,
        revision_number=result.revision_number,
        plan=result.plan,
    )


@router.post("/reasoning/storyboard/revise", response_model=StoryboardResponse)
async def revise_storyboard(
    request: ReviseStoryboardRequest,
    service: StoryboardSessionService = Depends(get_storyboard_service),
) -> StoryboardResponse:
    try:
        result = await service.revise_session(task_id=request.task_id, feedback=request.feedback)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MaxRevisionsExceededError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return StoryboardResponse(
        task_id=result.task_id,
        revision_number=result.revision_number,
        plan=result.plan,
    )


@router.post("/render", response_model=RenderFinalResponse)
async def render_final(
    request: RenderFinalRequest,
    service: StoryboardSessionService = Depends(get_storyboard_service),
) -> RenderFinalResponse:
    try:
        render_job = await service.render_final(task_id=request.task_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RenderFinalResponse(render_job_id=render_job.job_id, status=render_job.status.value)


@router.get("/render/{job_id}", response_model=RenderStatusResponse)
async def get_render_status(
    job_id: str,
    video_renderer=Depends(get_video_renderer),
) -> RenderStatusResponse:
    render_job = await video_renderer.get_status(job_id)
    return RenderStatusResponse(
        render_job_id=render_job.job_id,
        status=render_job.status.value,
        video_url=render_job.video_url,
        error=render_job.error,
    )