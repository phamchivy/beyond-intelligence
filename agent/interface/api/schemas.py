"""
Vi tri file nay: agent/interface/api/schemas.py

Pydantic request/response cho interface/api/ -- khop dung hinh dang
du lieu da dinh nghia trong docs/architecture/system-data-schemas.md
(cac buoc 4, 5, 7-revision, 9, 10). Day la tang DUY NHAT trong agent/
duoc phep dinh nghia schema HTTP -- application/business khong biet
FastAPI/Pydantic request model ton tai.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ReferenceAssetIn(BaseModel):
    """Anh tham chieu Backend gui kem (da la noi dung that -- xem buoc 3b/4 trong tai lieu)."""

    asset_role: str = Field(examples=["hero", "logo", "lifestyle"])
    mime_type: str = Field(examples=["image/jpeg", "image/png"])
    content_base64: str


class StartStoryboardRequest(BaseModel):
    """Body cho POST /agent/reasoning/storyboard -- khop buoc 4 trong system-data-schemas.md."""

    task_id: str
    brief: dict
    reference_assets: list[ReferenceAssetIn] = Field(default_factory=list)


class ReviseStoryboardRequest(BaseModel):
    """Body cho POST /agent/reasoning/storyboard/revise -- khop buoc 7 (nhanh needs_revision)."""

    task_id: str
    feedback: str


class StoryboardResponse(BaseModel):
    """Response chung cho ca start va revise -- khop buoc 5 trong system-data-schemas.md."""

    task_id: str
    revision_number: int
    storyboard_text: str


class RenderFinalRequest(BaseModel):
    """Body cho POST /agent/render -- khop buoc 9, chi can task_id (storyboard da duyet)."""

    task_id: str


class RenderFinalResponse(BaseModel):
    """Response ngay lap tuc sau submit -- Backend tu poll tiep qua render-status."""

    render_job_id: str
    status: str


class RenderStatusResponse(BaseModel):
    """Response cho GET /agent/render/{job_id} -- khop buoc 10."""

    render_job_id: str
    status: str
    video_url: str | None = None
    error: str | None = None


class FinalizeSessionRequest(BaseModel):
    task_id: str


class ErrorResponse(BaseModel):
    error: str
    detail: str