"""The FastAPI edge: `/health` and the hybrid retrieval query.

Holds no state and owns no data -- it reads Postgres and calls the same
functions Dagster calls. `POST /api/v1/assets` and
`GET /api/v1/assets/{id}` are not built here: both serve media artifacts
this pass does not produce.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from lib import db
from lib.embedding import embed
from lib.logging import get_logger, log_event
from lib.rerank import rerank
from lib.settings import settings

logger = get_logger(__name__)
app = FastAPI(title="Beyond Intelligence — Data API")


class DataQueryRequest(BaseModel):
    """Body for `POST /api/v1/data/query`."""

    q: str
    top_k: int = Field(default=settings.retrieval.top_k, ge=1)


class TrendingVideosRequest(BaseModel):
    """Body for `POST /api/v1/videos/trending`."""

    q: str
    top_k: int = Field(default=5, ge=1)


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


# ============================================================ trending video storyboards


def _trending_score(metadata: dict[str, Any], *, now: float) -> float:
    """Score one candidate video by revenue, decayed by how long ago it was fetched.

    Decay rather than a date cutoff: a hard "last N days" filter returns
    nothing at all on a thin bucket, and reads as a broken endpoint.

    Args:
        metadata: The chunk's metadata, carrying ``revenue`` and ``fetched_at``.
        now: Current Unix time, passed in so every candidate in one
            request is scored against the same instant.

    Returns:
        ``revenue`` halved once per ``trending_half_life_days`` of age.
    """
    revenue = float(metadata.get("revenue") or 0.0)
    fetched_at = metadata.get("fetched_at")
    if not fetched_at:
        return revenue
    age_days = max(0.0, (now - float(fetched_at)) / 86_400.0)
    return revenue * 0.5 ** (age_days / settings.retrieval.trending_half_life_days)


def _run_trending(q: str, top_k: int) -> dict[str, Any]:
    """Retrieve, then reorder by relevance (rerank score, trending as tiebreak).

    Nothing is dropped for scoring low -- ``settings.retrieval.rerank_min_score``
    is defined but not applied here yet (reorder only, no relevance gate).
    A cross-encoder score has no calibrated meaning across models, and a
    mistuned cutoff would silently hide legitimately relevant results the
    same way an absent one lets an irrelevant one rank #1 on revenue alone.

    Args:
        q: A product name or category name.
        top_k: How many videos to return, clamped to ``max_top_k``.

    Returns:
        `{"items": [...]}`, each item a video with its full storyboard.
    """
    top_k = min(top_k, settings.retrieval.max_top_k)
    qvec = embed([q])[0]
    candidates = db.search(
        q, qvec, top_k=settings.retrieval.candidate_k, source_type="video_storyboard"
    )

    scores = rerank(q, [c["content"] for c in candidates])
    now = time.time()
    ranked = sorted(
        zip(candidates, scores, strict=True),
        key=lambda pair: (pair[1], _trending_score(pair[0]["metadata"], now=now)),
        reverse=True,
    )

    items = []
    for chunk, score in ranked[:top_k]:
        meta = chunk["metadata"]
        items.append({
            "video_id": meta.get("video_id"),
            "title": meta.get("title"),
            "url": meta.get("url"),
            "category_name": meta.get("category_name"),
            "product_name": meta.get("product_name"),
            "revenue": meta.get("revenue"),
            "views": meta.get("views"),
            "ai_video": meta.get("ai_video"),
            "rerank_score": round(float(score), 4),
            "trending_score": round(_trending_score(meta, now=now), 2),
            "storyboard": meta.get("storyboard", {}),
        })

    log_event(logger, "info", "trending_videos_query", q=q, top_k=top_k,
              candidate_count=len(candidates), result_count=len(items))
    return {"items": items}


@app.get("/api/v1/videos/trending")
def trending_get(q: str, top_k: int = 5) -> dict[str, Any]:
    """GET variant: product or category name in, trending storyboards out."""
    return _run_trending(q, top_k)


@app.post("/api/v1/videos/trending")
def trending_post(body: TrendingVideosRequest) -> dict[str, Any]:
    """POST variant of the trending-videos endpoint."""
    return _run_trending(body.q, body.top_k)
