from io import BytesIO

from PIL import Image

from service.config import Settings
from service.imaging import CutoutFailed, UnsupportedImage, cutout_if_eligible, normalize

S = Settings(target_long_edge=256, s3_access_key="x", s3_secret_key="x")


def _png(w, h, mode="RGB"):
    buf = BytesIO()
    Image.new(mode, (w, h), "red").save(buf, "PNG")
    return buf.getvalue()


def test_downscale_preserves_aspect():
    out, mime, meta = normalize(_png(1024, 512), "hero", S)
    assert (meta["width"], meta["height"]) == (256, 128)
    assert mime == "image/jpeg"  # opaque hero flattens to JPEG


def test_never_upscales():
    _, _, meta = normalize(_png(100, 50), "hero", S)
    assert meta["width"] == 100


def test_logo_keeps_alpha():
    out, mime, _ = normalize(_png(300, 300, "RGBA"), "logo", S)
    assert mime == "image/png"
    assert Image.open(BytesIO(out)).mode == "RGBA"


def test_hero_flattens_alpha():
    _, mime, _ = normalize(_png(300, 300, "RGBA"), "hero", S)
    assert mime == "image/jpeg"


def test_rejects_non_image():
    try:
        normalize(b"not an image at all", "hero", S)
        assert False, "should have raised"
    except UnsupportedImage:
        pass


def test_cutout_role_policy(monkeypatch):
    monkeypatch.setattr("service.imaging.cutout", lambda b, s=None: b"PNGBYTES")
    S2 = S.model_copy(update={"cutout_roles_raw": "hero,closeup,variant"})
    assert cutout_if_eligible(_png(64, 64), "hero", S2) == b"PNGBYTES"
    assert cutout_if_eligible(_png(64, 64), "lifestyle", S2) is None  # background IS the content
    assert cutout_if_eligible(_png(64, 64), "logo", S2) is None  # already flat art


def test_cutout_failure_does_not_kill_the_asset(monkeypatch):
    def boom(b, s=None):
        raise CutoutFailed("model died")

    monkeypatch.setattr("service.imaging.cutout", boom)
    S2 = S.model_copy(update={"cutout_roles_raw": "hero,closeup,variant"})
    assert cutout_if_eligible(_png(64, 64), "hero", S2) is None  # falls back, never raises
