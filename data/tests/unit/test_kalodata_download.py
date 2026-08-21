"""Unit tests for scripts/kalodata_download_videos.py -- s3fs and yt-dlp are stubbed.

No network, no MinIO: Landing existence, the download, and the Bronze write
are all faked in-process.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import polars as pl
import pytest
import yt_dlp

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
        self.existing = set(existing or [])
        self.put_calls: list[tuple[str, str]] = []

    def glob(self, pattern: str) -> list[str]:
        return sorted(k for k in self.existing if fnmatch.fnmatch(k, pattern))

    def put(self, local_path: str, key: str) -> None:
        self.put_calls.append((local_path, key))
        self.existing.add(key)


_PREFIX = "bucket/trending_tiktok_videos/landing/beauty/electric_shaver/2026-08-21/"
_TIMESTAMP = "20260821T120000Z"

_ROW_A = {
    "video_id": "v1", "url": "https://www.tiktok.com/@alice/video/v1",
    "title": "vid A", "creator": "alice", "revenue": 100.0, "views": 1000,
    "ads_roas": 2.0, "ai_video": 0, "category_name": "Beauty", "product_name": "Electric Shaver",
}
_ROW_B = {
    "video_id": "v2", "url": "https://www.tiktok.com/@bob/video/v2",
    "title": "vid B", "creator": "bob", "revenue": 50.0, "views": 500,
    "ads_roas": 1.5, "ai_video": 1, "category_name": "Beauty", "product_name": "Electric Shaver",
}


@pytest.fixture(autouse=True)
def _no_real_download(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point yt_dlp.YoutubeDL at the fake, and reset its failure set each test.

    Also default Bronze to "doesn't exist yet" -- otherwise
    ``download_top_videos``'s cross-day dedup check would make a real
    Delta/S3 call every test. Tests that care about existing Bronze rows
    override ``table_version``/``read_delta`` themselves.
    """
    _FakeYoutubeDL.fail_urls = set()
    monkeypatch.setattr(d.yt_dlp, "YoutubeDL", _FakeYoutubeDL)
    monkeypatch.setattr(d, "table_version", lambda *a, **kw: None)


def test_slug_collapses_unsafe_characters():
    assert d._slug("Beauty & Personal Care!!") == "Beauty_Personal_Care"
    assert d._slug("  ") == "unknown"
    assert d._slug("") == "unknown"


def test_day_prefix_nests_by_category_then_product_then_date():
    prefix = d._day_prefix("Beauty & Care", "Electric Shaver!!", "2026-08-21")
    assert prefix == (
        f"{d.settings.storage.url.replace('s3://', '')}/trending_tiktok_videos/landing/"
        "Beauty_Care/Electric_Shaver/2026-08-21/"
    )


def test_landing_key_embeds_slugged_title_video_id_and_timestamp():
    key = d._landing_key(_PREFIX, "Cool Video! #trend", "v1", _TIMESTAMP)
    assert key == f"{_PREFIX}Cool_Video_trend_v1_{_TIMESTAMP}.mp4"


def test_existing_key_matches_by_video_id_regardless_of_title_or_timestamp():
    fs = _FakeS3(existing={f"{_PREFIX}some_old_title_v1_20260101T000000Z.mp4"})
    assert d._existing_key(fs, _PREFIX, "v1") is not None
    assert d._existing_key(fs, _PREFIX, "v2") is None


def test_existing_video_is_skipped_without_downloading():
    existing_key = d._landing_key(_PREFIX, "old title", "v1", "20260101T000000Z")
    fs = _FakeS3(existing={existing_key})

    result = d._download_one(fs, _ROW_A, "electric shaver", _PREFIX, _TIMESTAMP)

    assert result.skipped is True
    assert result.downloaded is False
    assert result.row is None
    assert fs.put_calls == []  # never touched the network path


def test_new_video_downloads_and_uploads_to_landing():
    fs = _FakeS3()
    result = d._download_one(fs, _ROW_A, "electric shaver", _PREFIX, _TIMESTAMP)

    assert result.downloaded is True
    assert result.row["video_id"] == "v1"
    assert result.row["sha256"]  # computed from the (fake) written bytes
    assert result.row["duration_s"] == 42
    assert result.row["category_name"] == "Beauty"
    assert result.row["product_name"] == "Electric Shaver"

    expected_key = d._landing_key(_PREFIX, "vid A", "v1", _TIMESTAMP)
    assert fs.put_calls[0][1] == expected_key


def test_a_failed_download_does_not_abort_the_rest(monkeypatch: pytest.MonkeyPatch):
    _FakeYoutubeDL.fail_urls = {_ROW_A["url"]}
    monkeypatch.setattr(d, "top_videos", lambda keyword, **kw: [_ROW_A, _ROW_B])
    monkeypatch.setattr(d, "s3_filesystem", lambda: _FakeS3())

    results = d.download_top_videos("electric shaver", limit=2)

    assert [r.downloaded for r in results] == [False, True]
    assert results[0].row is None
    assert results[1].row["video_id"] == "v2"


def test_download_top_videos_is_a_noop_when_nothing_ranked(monkeypatch: pytest.MonkeyPatch):
    """No ranked videos means no category/product to build a prefix from."""
    monkeypatch.setattr(d, "top_videos", lambda keyword, **kw: [])
    assert d.download_top_videos("no such product") == []


def test_bronze_row_carries_the_kalodata_metrics_through(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(d, "top_videos", lambda keyword, **kw: [_ROW_A, _ROW_B])
    monkeypatch.setattr(d, "s3_filesystem", lambda: _FakeS3())
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
    assert rows[0]["category_name"] == "Beauty"


def test_a_video_already_in_bronze_from_any_day_is_skipped_before_yt_dlp_runs(
    monkeypatch: pytest.MonkeyPatch,
):
    """A video still trending on day 2 must not be re-downloaded from scratch."""
    monkeypatch.setattr(d, "top_videos", lambda keyword, **kw: [_ROW_A, _ROW_B])
    monkeypatch.setattr(d, "s3_filesystem", lambda: _FakeS3())
    monkeypatch.setattr(d, "table_version", lambda *a, **kw: 0)
    monkeypatch.setattr(
        d, "read_delta", lambda *a, **kw: pl.DataFrame({"video_id": ["v1"]}).to_arrow()
    )

    results = d.download_top_videos("electric shaver", limit=2)

    by_id = {r.video_id: r for r in results}
    assert by_id["v1"].skipped is True
    assert by_id["v1"].downloaded is False
    assert by_id["v1"].row is None
    assert by_id["v2"].downloaded is True  # not in Bronze yet -- still fetched


def test_write_bronze_is_a_noop_when_nothing_downloaded():
    all_skipped = [d.FetchResult("v1", None, downloaded=False, skipped=True)]
    assert d._write_bronze(all_skipped) is None
