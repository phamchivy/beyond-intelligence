"""
Vi tri file nay: data/interface/api/main.py

Diem vao FastAPI cua data/. Chay bang:
    uvicorn interface.api.main:app --reload --port 8002
(chay tu thu muc data/).
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from bootstrap.container import _build_llm, _build_market_data_provider
from config.settings import settings
from interface.api.insight_routes import router as insight_router
from observability.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Beyond Intelligence - Data Service",
    description="Kalodata insight aggregation service",
    version="0.1.0",
)

app.include_router(insight_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    task_id = None
    if request.method == "POST":
        try:
            body = await request.json()
            task_id = body.get("task_id")
        except Exception:
            pass

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"HTTP_{exc.status_code}", "message": exc.detail, "task_id": task_id}},
    )


@app.get("/health")
async def health() -> JSONResponse:
    dependencies: dict[str, str] = {}
    healthy = True

    try:
        _build_llm(settings)
        dependencies["llm"] = f"ok ({settings.llm.provider.value})"
    except Exception as exc:
        dependencies["llm"] = f"error: {exc}"
        healthy = False

    try:
        settings.kalodata.require_api_key()
        dependencies["kalodata"] = "ok"
    except Exception as exc:
        dependencies["kalodata"] = f"error: {exc}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if healthy else "degraded", "dependencies": dependencies},
    )