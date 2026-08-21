"""
Pure image processing -- no network, no S3, no Postgres. This is what
makes tests/unit/test_imaging.py runnable offline.

normalize(): unpredictable upload -> predictable image (size, orientation,
colour mode, no metadata).

cutout() / cutout_if_eligible(): background removal via segmentation
(never generative -- see the module docstring in cutout_if_eligible).
"""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Any

from PIL import Image, ImageOps

from service.config import Settings, settings as default_settings

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class UnsupportedImage(Exception):
    pass


class CutoutFailed(Exception):
    pass


def _configure_pillow(s: Settings) -> None:
    Image.MAX_IMAGE_PIXELS = s.max_image_pixels


def normalize(raw: bytes, role: str, s: Settings | None = None) -> tuple[bytes, str, dict[str, Any]]:
    """Return (processed_bytes, mime_type, metadata). Raises UnsupportedImage."""
    s = s or default_settings
    _configure_pillow(s)

    try:
        im = Image.open(BytesIO(raw))
        im.load()
    except Exception as e:
        raise UnsupportedImage(f"khong doc duoc anh: {e}") from e

    source_format = im.format
    if source_format not in _ALLOWED_FORMATS:
        raise UnsupportedImage(f"dinh dang khong ho tro: {source_format}")

    im = ImageOps.exif_transpose(im)

    had_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    keep_alpha = had_alpha and role == "logo"

    if keep_alpha:
        im = im.convert("RGBA")
    else:
        if im.mode in ("RGBA", "LA"):
            background = Image.new("RGB", im.size, (255, 255, 255))
            background.paste(im, mask=im.split()[-1])
            im = background
        else:
            im = im.convert("RGB")

    long_edge = max(im.size)
    if long_edge > s.target_long_edge:
        scale = s.target_long_edge / long_edge
        new_size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
        im = im.resize(new_size, Image.LANCZOS)

    buf = BytesIO()
    if keep_alpha:
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.save(buf, "JPEG", quality=s.jpeg_quality, progressive=True)
        mime = "image/jpeg"

    processed = buf.getvalue()
    metadata = {
        "width": im.width,
        "height": im.height,
        "bytes": len(processed),
        "source_format": source_format,
        "had_alpha": had_alpha,
    }
    return processed, mime, metadata


@lru_cache(maxsize=1)
def _rembg_session(model_name: str):
    from rembg import new_session

    return new_session(model_name)


def warm_cutout(s: Settings | None = None) -> None:
    """Build the onnxruntime session eagerly so its 2-5s cost lands at
    startup (FastAPI lifespan), not on the first user's request."""
    s = s or default_settings
    if s.cutout_backend == "rembg":
        _rembg_session(s.cutout_model)


def cutout(normalized: bytes, s: Settings | None = None) -> bytes:
    """RGBA PNG with the background alpha-ed out. Raises CutoutFailed."""
    s = s or default_settings
    if s.cutout_backend == "none":
        raise CutoutFailed("cutout backend la 'none'")

    try:
        if s.cutout_backend == "rembg":
            from rembg import remove

            session = _rembg_session(s.cutout_model)
            result = remove(normalized, session=session)
            im = Image.open(BytesIO(result)).convert("RGBA")
            buf = BytesIO()
            im.save(buf, "PNG", optimize=True)
            return buf.getvalue()
        elif s.cutout_backend == "replicate":
            raise CutoutFailed("replicate backend chua duoc trien khai")
        else:
            raise CutoutFailed(f"backend khong ro: {s.cutout_backend}")
    except CutoutFailed:
        raise
    except Exception as e:
        raise CutoutFailed(str(e)) from e


# Roles where removing the background destroys the asset's meaning:
# lifestyle shots ARE their background; logos are already flat art and
# a matting model only softens their edges. Never route these through
# cutout(), regardless of backend.
_EXCLUDED_ROLES = {"lifestyle", "logo"}


def is_cutout_eligible(role: str, s: Settings | None = None) -> bool:
    s = s or default_settings
    return role not in _EXCLUDED_ROLES and role in s.cutout_roles


def cutout_if_eligible(normalized: bytes, role: str, s: Settings | None = None) -> bytes | None:
    """
    Policy wrapper around cutout(): None if the role is excluded, None
    (never raises) if the model fails. A cutout is an enhancement --
    losing it must never fail the asset it belongs to.
    """
    s = s or default_settings
    if not is_cutout_eligible(role, s):
        return None
    try:
        return cutout(normalized, s)
    except CutoutFailed:
        return None
