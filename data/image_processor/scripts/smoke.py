"""
Stands in for the Backend under the amended flow: uploads a raw image to
MinIO directly (as Backend now does), then drives the Data pod through
its real HTTP API. Doubles as the integration test until the .NET side
of this contract exists.

Usage:
    python scripts/smoke.py

Requires: MinIO + the service running.
"""
from __future__ import annotations

import os
import sys
import time
from io import BytesIO
from uuid import uuid4

import httpx
from PIL import Image

sys.path.insert(0, ".")
from service import storage  # noqa: E402
from service.config import settings  # noqa: E402

BASE_URL = os.environ.get("DATA_SERVICE_URL", "http://localhost:8002")
HEADERS = {"X-Internal-Token": settings.internal_token}


def make_sample_jpeg(w=3000, h=2000) -> bytes:
    im = Image.new("RGB", (w, h), (200, 60, 60))
    buf = BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def main() -> None:
    task_id = str(uuid4())
    asset_id = str(uuid4())
    raw_key = f"{task_id}/{asset_id}.jpg"

    print(f"[1/5] task_id={task_id} asset_id={asset_id}")
    print(f"[2/5] uploading raw JPEG (target: {settings.s3_bucket or settings.bucket_raw}) -- simulating Backend upload")
    storage.put_bytes(settings.bucket_raw, raw_key, make_sample_jpeg(), "image/jpeg")

    print("[3/5] POST /data/assets/process")
    t0 = time.time()
    resp = httpx.post(
        f"{BASE_URL}/data/assets/process",
        headers=HEADERS,
        json={
            "task_id": task_id,
            "assets": [
                {
                    "asset_id": asset_id,
                    "object_key": raw_key,
                    "asset_role": "hero",
                    "mime_type": "image/jpeg",
                }
            ],
        },
        timeout=60,
    )
    elapsed = time.time() - t0
    resp.raise_for_status()
    body = resp.json()
    print(f"      status={resp.status_code} elapsed={elapsed:.1f}s")
    assert not body["failed"], f"asset failed: {body['failed']}"
    asset = body["assets"][0]
    print(f"      object_ref={asset['object_ref']}")
    print(f"      cutout_ref={asset['cutout_ref']}")
    print(f"      metadata={asset['metadata']}")

    assert asset["object_presigned_url"], "expected an object_presigned_url for the normalized image"
    dl = httpx.get(asset["object_presigned_url"], timeout=30)
    dl.raise_for_status()
    Image.open(BytesIO(dl.content)).verify()
    print(f"      normalized image fetched via object_presigned_url OK ({len(dl.content)} bytes)")

    if asset["cutout_presigned_url"]:
        print("[4/5] fetching cutout_presigned_url")
        r = httpx.get(asset["cutout_presigned_url"], timeout=30)
        r.raise_for_status()
        im = Image.open(BytesIO(r.content))
        assert im.mode == "RGBA", f"expected RGBA cutout, got {im.mode}"
        alphas = im.getchannel("A").getextrema()
        print(f"      cutout PNG mode={im.mode} alpha_range={alphas}")
        assert alphas[0] < 255 or alphas[1] < 255, (
            "alpha channel is fully opaque -- cutout model likely did not run"
        )
    else:
        print("[4/5] no cutout_presigned_url returned (metadata.cutout=%s) -- skipping fetch check" % asset["metadata"]["cutout"])

    print("[5/5] smoke test passed")


if __name__ == "__main__":
    main()
