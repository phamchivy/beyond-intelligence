"""The FastAPI edge: `/health` and the hybrid retrieval query.

Holds no state and owns no data -- it reads Postgres and calls the same
functions Dagster calls. `POST /api/v1/assets` and
`GET /api/v1/assets/{id}` are not built here: both serve media artifacts
this pass does not produce.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from lib import db
from lib.embedding import embed
from lib.logging import get_logger, log_event
from lib.settings import settings

logger = get_logger(__name__)
app = FastAPI(title="Beyond Intelligence — Data API")


class DataQueryRequest(BaseModel):
    """Body for `POST /api/v1/data/query`."""

    q: str
    top_k: int = Field(default=settings.retrieval.top_k, ge=1)


class ApiError(Exception):
    """Raised to produce the shared `{"error": {...}}` envelope (decision 8.7)."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        """Build the error with its code, message, and HTTP status."""
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    """Render every ApiError as the shared error envelope, matching the other pods."""
    request_id = uuid.uuid4().hex[:12]
    log_event(logger, "error", "api_error", code=exc.code, request_id=request_id,
              path=str(request.url.path))
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "request_id": request_id}},
    )


@app.on_event("startup")
def startup() -> None:
    """Apply the (idempotent) init SQL so the API is self-sufficient against a fresh database."""
    db.apply_init_sql()


@app.get("/health")
def health() -> dict[str, Any]:
    """Always 200 while the process is alive (decision 8.6).

    A 503 during a database blip would fail the compose healthcheck and
    stop the other pods from ever starting, so `status` carries the
    signal instead of the status code.
    """
    try:
        chunks = db.chunk_count()
        return {"status": "ok", "db": True, "chunks": chunks}
    except Exception:
        return {"status": "degraded", "db": False, "chunks": 0}


def _normalise_scores(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalise RRF scores to [0, 1] by the maximum in the returned set.

    This is presentation only -- RRF ranks, it does not score. Fused
    values cluster near 1/61 ≈ 0.016, and mapping that straight into a
    caller's confidence field would read as near-zero.
    """
    if not items:
        return items
    max_score = max(item["score"] for item in items) or 1.0
    for item in items:
        item["score"] = round(item["score"] / max_score, 4)
    return items


def _run_query(q: str, top_k: int) -> dict[str, Any]:
    """Shared body for both the GET and POST `/api/v1/data/query` routes.

    Args:
        q: The query text.
        top_k: Requested result count, clamped to `settings.retrieval.max_top_k`.

    Returns:
        The response body: `{"items": [{"id", "text", "score", "metadata"}]}`
        -- a shape dictated by `agent/`'s `HttpJsonRetriever`, not chosen here.
    """
    top_k = min(top_k, settings.retrieval.max_top_k)
    qvec = embed([q])[0]
    rows = db.search(q, qvec, top_k=top_k)
    items = [
        {"id": r["chunk_id"], "text": r["content"], "score": float(r["score"]),
         "metadata": r["metadata"]}
        for r in rows
    ]
    items = _normalise_scores(items)
    log_event(logger, "info", "retrieval_query", q=q, top_k=top_k, result_count=len(items))
    return {"items": items}


@app.get("/api/v1/data/query")
def query_get(q: str, top_k: int = settings.retrieval.top_k) -> dict[str, Any]:
    """GET variant of the query endpoint -- what `agent/`'s HttpJsonRetriever issues."""
    return _run_query(q, top_k)


@app.post("/api/v1/data/query")
def query_post(body: DataQueryRequest) -> dict[str, Any]:
    """POST variant of the query endpoint -- what integration-architecture.md specifies."""
    return _run_query(body.q, body.top_k)
