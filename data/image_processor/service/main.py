"""
FastAPI app for the Data pod. One real route + health:

  POST /data/assets/process    normalize + cutout, return presigned URLs
  GET  /health                 no auth

See hackathon_docs/data-image-processing-blueprint.md for background (note:
that doc also describes /data/storage/{key} and /data/videos/persist, which
this service no longer implements -- see image-processor-docs.md for why).
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Response

from service import storage
from service.config import settings
from service.imaging import (
    CutoutFailed,
    UnsupportedImage,
    cutout,
    is_cutout_eligible,
    normalize,
    warm_cutout,
)
from service.schemas import AssetFailure, AssetMetadata, AssetOut, ProcessRequest, ProcessResponse

logger = logging.getLogger("data.service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_buckets()
    await asyncio.to_thread(warm_cutout)
    yield


app = FastAPI(title="Data pod", lifespan=lifespan)


def require_token(x_internal_token: str | None = Header(default=None)) -> None:
    if x_internal_token != settings.internal_token:
        raise HTTPException(status_code=401, detail="thieu hoac sai X-Internal-Token")


@app.get("/health")
def health():
    return {"status": "ok"}


def _process_one(asset, task_id: str) -> AssetOut:
    key = storage.validate_raw_key(asset.object_key, task_id)

    meta = storage.head(settings.bucket_raw, key)
    size = meta.get("ContentLength", 0)
    if size > settings.max_asset_bytes:
        raise UnsupportedImage(f"file qua lon: {size} bytes")

    raw = storage.get_bytes(settings.bucket_raw, key)
    processed, mime, img_meta = normalize(raw, asset.asset_role)

    ext = "png" if mime == "image/png" else "jpg"
    processed_key = f"{task_id}/{asset.asset_id}_{asset.asset_role}.{ext}"
    storage.put_bytes(settings.bucket_processed, processed_key, processed, mime)

    cutout_ref = None
    cutout_presigned_url = None
    cutout_status = "skipped"
    if is_cutout_eligible(asset.asset_role):
        try:
            cutout_bytes = cutout(processed)
            cutout_key = f"{task_id}/{asset.asset_id}_{asset.asset_role}_cutout.png"
            storage.put_bytes(settings.bucket_processed, cutout_key, cutout_bytes, "image/png")
            cutout_ref = f"{settings.bucket_processed}/{cutout_key}"
            cutout_presigned_url = storage.presign(settings.bucket_processed, cutout_key)
            cutout_status = "ok"
        except CutoutFailed:
            logger.warning("cutout that bai cho asset %s, giu anh da chuan hoa", asset.asset_id)
            cutout_status = "failed"

    return AssetOut(
        asset_id=asset.asset_id,
        asset_role=asset.asset_role,
        mime_type=mime,
        object_presigned_url=storage.presign(settings.bucket_processed, processed_key),
        object_ref=f"{settings.bucket_processed}/{processed_key}",
        cutout_ref=cutout_ref,
        cutout_presigned_url=cutout_presigned_url,
        metadata=AssetMetadata(**img_meta, cutout=cutout_status),
    )


@app.post("/data/assets/process", response_model=ProcessResponse, status_code=200)
async def process_assets(req: ProcessRequest, response: Response, _: None = Depends(require_token)):
    sem = asyncio.Semaphore(settings.cutout_concurrency)
    results: list[AssetOut] = []
    failed: list[AssetFailure] = []

    async def run(asset):
        async with sem:
            try:
                out = await asyncio.to_thread(_process_one, asset, req.task_id)
                results.append(out)
            except storage.InvalidKey as e:
                failed.append(AssetFailure(asset_id=asset.asset_id, reason=f"invalid_key: {e}"))
            except storage.ObjectNotFound:
                failed.append(AssetFailure(asset_id=asset.asset_id, reason="raw_object_missing"))
            except UnsupportedImage as e:
                failed.append(AssetFailure(asset_id=asset.asset_id, reason=f"unsupported_format: {e}"))
            except Exception as e:  # noqa: BLE001 -- one bad asset must not kill the batch
                logger.exception("loi khong mong doi khi xu ly asset %s", asset.asset_id)
                failed.append(AssetFailure(asset_id=asset.asset_id, reason=f"internal_error: {e}"))

    await asyncio.gather(*(run(a) for a in req.assets))

    response_body = ProcessResponse(assets=results, failed=failed)
    if not results and req.assets:
        raise HTTPException(status_code=422, detail=response_body.model_dump())
    if failed:
        response.status_code = 207  # partial success -- some assets processed, some didn't
    return response_body
