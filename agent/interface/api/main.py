"""
Vi tri file nay: agent/interface/api/main.py

Diem vao FastAPI cua agent/ -- day la tang Interface (tang thu 4, truoc
day agent/ moi co Application/Domain/Infrastructure). Chay bang:

    uvicorn interface.api.main:app --reload --port 8001

(chay tu thu muc agent/, dung quy uoc da thong nhat tu dau du an).
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from bootstrap.container import _build_llm, _build_video_renderer
from config.settings import settings
from interface.api.storyboard_routes import router as storyboard_router
from observability.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Beyond Intelligence - Agent Service",
    description="AI Ads Video Generator - storyboard reasoning + video render",
    version="0.1.0",
)

app.include_router(storyboard_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Override dinh dang mac dinh cua FastAPI ({"detail": "..."}) sang
    format thong nhat da chot -- GIU NGUYEN status_code (404/409...) do
    tung route tu quyet dinh (xem storyboard_routes.py), chi doi hinh
    dang body cho khop quy uoc chung giua cac pod.
    """
    task_id = None
    if request.method == "POST":
        try:
            body = await request.json()
            task_id = body.get("task_id")
        except Exception:
            pass

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "task_id": task_id,
            }
        },
    )


@app.exception_handler(Exception)
async def unified_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Dinh dang loi THONG NHAT giua cac pod, dung theo dung quy uoc da
    chot trong docs/architecture/integration-architecture.md muc 6:

        {"error": {"code": "...", "message": "...", "task_id": "..."}}

    Ap dung cho loi KHONG DUOC bat rieng (uncaught) -- cac loi domain
    da biet (SessionNotFoundError, MaxRevisionsExceededError...) van
    duoc convert rieng trong tung route (xem storyboard_routes.py) de
    tra dung status code (404/409), handler nay la luoi an toan cuoi
    cung cho loi bat ngo (500).
    """
    task_id = None
    if request.method == "POST":
        try:
            body = await request.json()
            task_id = body.get("task_id")
        except Exception:
            pass

    logger.error(
        "unhandled_exception",
        extra={"extra_fields": {"path": request.url.path, "error": str(exc)}},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": type(exc).__name__,
                "message": str(exc),
                "task_id": task_id,
            }
        },
    )


@app.get("/health")
async def health() -> JSONResponse:
    """
    Kiem tra THAT trang thai phu thuoc (khong chi tra cung "ok") --
    dung dung yeu cau da chot trong integration-architecture.md: xac
    nhan cau hinh LLM/Video provider hop le (co du key/model/base_url
    can thiet), KHONG goi API that ra ngoai (tranh health check cham/
    ton tien) -- chi validate config, dung nguyen tac 'fail fast' da
    ap dung cho require_api_key()/require_config().
    """
    dependencies: dict[str, str] = {}
    healthy = True

    try:
        _build_llm(settings)
        dependencies["llm"] = f"ok ({settings.llm.provider.value})"
    except Exception as exc:
        dependencies["llm"] = f"error: {exc}"
        healthy = False

    try:
        _build_video_renderer(settings)
        dependencies["video_renderer"] = f"ok ({settings.video.provider.value})"
    except Exception as exc:
        dependencies["video_renderer"] = f"error: {exc}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if healthy else "degraded", "dependencies": dependencies},
    )