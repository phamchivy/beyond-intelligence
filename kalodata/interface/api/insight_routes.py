"""
Vi tri file nay: data/interface/api/insight_routes.py

Route HTTP mong -- chi goi vao InsightService, khong chua logic nghiep vu.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from application.services.insight_service import (
    InsightService,
    InsightResult,
    MaxRevisionsExceededError,
    SessionNotFoundError,
)
from bootstrap.container import build_insight_service
from interface.api.schemas import InsightResponse, ReviseInsightRequest, StartInsightRequest

router = APIRouter(prefix="/data", tags=["insight"])

_insight_service: InsightService | None = None


def get_insight_service() -> InsightService:
    global _insight_service
    if _insight_service is None:
        _insight_service = build_insight_service()
    return _insight_service


def _to_response(result: InsightResult) -> InsightResponse:
    return InsightResponse(
        task_id=result.task_id,
        revision_number=result.revision_number,
        criteria=result.criteria,
        insight_text=result.insight_text,
    )


@router.post("/insights", response_model=InsightResponse)
async def start_insight(
    request: StartInsightRequest,
    service: InsightService = Depends(get_insight_service),
) -> InsightResponse:
    result = await service.start_session(task_id=request.task_id, brief=request.brief)
    return _to_response(result)


@router.post("/insights/revise", response_model=InsightResponse)
async def revise_insight(
    request: ReviseInsightRequest,
    service: InsightService = Depends(get_insight_service),
) -> InsightResponse:
    try:
        result = await service.revise_session(task_id=request.task_id, feedback=request.feedback)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MaxRevisionsExceededError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _to_response(result)