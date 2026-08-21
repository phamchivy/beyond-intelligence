"""Unit tests for scripts/kalodata_download_videos.py -- s3fs and yt-dlp are stubbed.

No network, no MinIO: Landing existence, the download, and the Bronze write
are all faked in-process.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yt_dlp

from lib.settings import settings
from scripts import kalodata_download_videos as d


class _FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL: writes a few bytes, returns fake info.

    ``fail_urls`` names the video URLs that should raise DownloadError
    instead of "downloading" -- the failure path under test.
    """

    fail_urls: set[str] = set()

    def __init__(self, opts: dict) -> None:
        self._opts = opts

    def __enter__(self) -> "_FakeYoutubeDL":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict:
        if url in self.fail_urls:
            raise yt_dlp.utils.DownloadError("boom")
        Path(self._opts["outtmpl"]).write_bytes(b"fake mp4 bytes")
        return {"duration": 42}


class _FakeS3:
    """Stands in for s3fs.S3FileSystem: an in-memory set of existing keys."""

    def __init__(self, existing: set[str] | None = None) -> None:
        self.existing = existing or set()
        self.put_calls: list[tuple[str, str]] = []

    def exists(self, key: str) -> bool:
        return key in self.existing

    def put(self, local_path: str, key: str) -> None:
        self.put_calls.append((local_path, key))
        self.existing.add(key)


_ROW_A = {
    "video_id": "v1", "url": "https://www.tiktok.com/@alice/video/v1",
    "title": "vid A", "creator": "alice", "revenue": 100.0, "views": 1000,
    "ads_roas": 2.0, "ai_video": 0,
}
_ROW_B = {
    "video_id": "v2", "url": "https://www.tiktok.com/@bob/video/v2",
    "title": "vid B", "creator": "bob", "revenue": 50.0, "views": 500,
    "ads_roas": 1.5, "ai_video": 1,
}


@pytest.fixture(autouse=True)
def _no_real_download(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point yt_dlp.YoutubeDL at the fake, and reset its failure set each test."""
    _FakeYoutubeDL.fail_urls = set()
    monkeypatch.setattr(d.yt_dlp, "YoutubeDL", _FakeYoutubeDL)


def test_landing_key_is_scoped_under_tiktok_by_video_id():
    key = d._landing_key("7404191282148511007")
    root = settings.storage.landing_url.replace("s3://", "")
    assert key == f"{root}/tiktok/7404191282148511007.mp4"


def test_existing_video_is_skipped_without_downloading():
    fs = _FakeS3(existing={d._landing_key("v1")})
    result = d._download_one(fs, _ROW_A, keyword="electric shaver")

    assert result.skipped is True
    assert result.downloaded is False
    assert result.row is None
    assert fs.put_calls == []  # never touched the network path


def test_new_video_downloads_and_uploads_to_landing():
    fs = _FakeS3()
    result = d._download_one(fs, _ROW_A, keyword="electric shaver")

    assert result.downloaded is True
    assert result.row["video_id"] == "v1"
    assert result.row["sha256"]  # computed from the (fake) written bytes
    assert result.row["duration_s"] == 42
    assert fs.put_calls[0][1] == d._landing_key("v1")


def test_a_failed_download_does_not_abort_the_rest(monkeypatch: pytest.MonkeyPatch):
    _FakeYoutubeDL.fail_urls = {_ROW_A["url"]}
    monkeypatch.setattr(d, "top_videos", lambda keyword, **kw: [_ROW_A, _ROW_B])
    monkeypatch.setattr(d, "_landing_fs", lambda: _FakeS3())

    results = d.download_top_videos("electric shaver", limit=2)

    assert [r.downloaded for r in results] == [False, True]
    assert results[0].row is None
    assert results[1].row["video_id"] == "v2"


def test_bronze_row_carries_the_kalodata_metrics_through(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(d, "top_videos", lambda keyword, **kw: [_ROW_A, _ROW_B])
    monkeypatch.setattr(d, "_landing_fs", lambda: _FakeS3())
    results = d.download_top_videos("electric shaver", limit=2)

    captured: dict = {}
    monkeypatch.setattr(
        d, "write_delta",
        lambda layer, name, table, **kw: captured.update(layer=layer, name=name, table=table)
        or 3,
    )
    version = d._write_bronze(results)

    assert version == 3
    assert captured["layer"] == "bronze"
    assert captured["name"] == "tiktok_video"
    rows = captured["table"].to_pylist()
    assert {r["video_id"] for r in rows} == {"v1", "v2"}
    assert rows[0]["revenue"] in (100.0, 50.0)  # the Kalodata metric survived


def test_write_bronze_is_a_noop_when_nothing_downloaded():
    all_skipped = [d.FetchResult("v1", None, downloaded=False, skipped=True)]
    assert d._write_bronze(all_skipped) is None
