"""Unit tests for scripts/kalodata_analyze_videos.py -- Gemini and s3fs are stubbed.

No network, no S3, no API key: read_delta/table_version/write_delta and
analyze_video are all faked in-process.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pyarrow as pa
import pytest

from scripts import kalodata_analyze_videos as a


class _FakeS3:
    """Stands in for s3fs.S3FileSystem: writes a few bytes on .get()."""

    def get(self, rpath: str, lpath: str) -> None:
        Path(lpath).write_bytes(b"fake mp4 bytes")


_BRONZE_ROWS = [
    {
        "video_id": "v1", "s3_key": "bucket/v1.mp4", "revenue": 100.0, "views": 1000,
        "ai_video": 0, "category_name": "Beauty", "product_name": "Shaver",
        "title": "vid A", "fetched_at": 200,
    },
    {
        "video_id": "v2", "s3_key": "bucket/v2.mp4", "revenue": 50.0, "views": 500,
        "ai_video": 1, "category_name": "Beauty", "product_name": "Shaver",
        "title": "vid B", "fetched_at": 100,
    },
]

_STORYBOARD = {
    "hook": "Grab attention fast",
    "hook_style": "Fast cuts with bold on-screen text",
    "cta": "Buy now",
    "summary": "Shaver demo",
    "scenes": [
        {"scene_no": 0, "t_start": 0.0, "t_end": 3.0, "shot_type": "close-up",
         "visual": "hands holding shaver", "on_screen_text": "NEW", "voiceover": "Check this out"},
        {"scene_no": 1, "t_start": 3.0, "t_end": 6.0, "shot_type": "wide",
         "visual": "using shaver", "on_screen_text": "", "voiceover": "So smooth"},
    ],
}


def _arrow(rows: list[dict]) -> pa.Table:
    return pl.DataFrame(rows).to_arrow()


@pytest.fixture(autouse=True)
def _prompt_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin prompt_version so tests don't depend on ambient .env."""
    monkeypatch.setattr(a.settings.gemini, "prompt_version", "storyboard-v1")


@pytest.fixture
def stub_tables(monkeypatch: pytest.MonkeyPatch):
    """Return a factory wiring table_version/read_delta to canned Bronze/Silver data."""
    def install(*, bronze: list[dict] | None, silver: list[dict] | None) -> None:
        versions = {"bronze/tiktok_video": bronze, "silver/video_storyboard": silver}

        def fake_table_version(layer: str, name: str) -> int | None:
            return 0 if versions[f"{layer}/{name}"] is not None else None

        def fake_read_delta(layer: str, name: str, **kw) -> pa.Table:
            return _arrow(versions[f"{layer}/{name}"])

        monkeypatch.setattr(a, "table_version", fake_table_version)
        monkeypatch.setattr(a, "read_delta", fake_read_delta)
        monkeypatch.setattr(a, "s3_filesystem", lambda: _FakeS3())

    return install


def test_already_analyzed_video_is_skipped_with_zero_model_calls(
    monkeypatch: pytest.MonkeyPatch, stub_tables
):
    stub_tables(
        bronze=_BRONZE_ROWS,
        silver=[{
            "video_id": "v1", "prompt_version": "storyboard-v1", "scene_no": 0,
            "t_start": 0.0, "t_end": 1.0, "shot_type": "x", "visual": "x",
            "on_screen_text": "", "voiceover": "", "hook": "h", "cta": "c", "summary": "s",
        }],
    )
    calls: list[str] = []
    monkeypatch.setattr(
        a, "analyze_video",
        lambda path, **kw: calls.append(Path(path).stem) or _STORYBOARD,
    )

    results, skipped = a.analyze_top_videos()

    assert skipped == 1
    assert [r.video_id for r in results] == ["v2"]
    assert calls == ["v2"]  # v1 never touched Gemini


def test_prompt_version_bump_forces_recompute(monkeypatch: pytest.MonkeyPatch, stub_tables):
    stub_tables(
        bronze=_BRONZE_ROWS,
        silver=[{
            "video_id": "v1", "prompt_version": "storyboard-v0", "scene_no": 0,
            "t_start": 0.0, "t_end": 1.0, "shot_type": "x", "visual": "x",
            "on_screen_text": "", "voiceover": "", "hook": "h", "cta": "c", "summary": "s",
        }],
    )
    monkeypatch.setattr(a, "analyze_video", lambda path, **kw: _STORYBOARD)

    results, skipped = a.analyze_top_videos()

    assert skipped == 0
    assert {r.video_id for r in results} == {"v1", "v2"}


def test_a_failed_analysis_does_not_abort_the_rest(monkeypatch: pytest.MonkeyPatch, stub_tables):
    stub_tables(bronze=_BRONZE_ROWS, silver=None)

    def flaky_analyze(path, **kw):
        if Path(path).stem == "v1":
            raise RuntimeError("Gemini upload failed")
        return _STORYBOARD

    monkeypatch.setattr(a, "analyze_video", flaky_analyze)

    results, _ = a.analyze_top_videos()

    by_id = {r.video_id: r for r in results}
    assert by_id["v1"].analyzed is False
    assert by_id["v1"].scenes == []
    assert by_id["v2"].analyzed is True
    assert len(by_id["v2"].scenes) == 2


def test_analyze_one_quarantines_a_storyboard_whose_timestamps_overrun_duration(
    monkeypatch: pytest.MonkeyPatch,
):
    """Gemini claiming a scene past the video's real length must not reach Silver."""
    monkeypatch.setattr(a, "analyze_video", lambda path, **kw: _STORYBOARD)
    writes: list[tuple[str, str, int]] = []
    monkeypatch.setattr(
        a, "write_delta",
        lambda layer, name, table, **kw: writes.append((layer, name, table.num_rows)) or 1,
    )
    bronze_row = {**_BRONZE_ROWS[0], "duration_s": 5.0}  # _STORYBOARD's last scene ends at 6.0

    result = a._analyze_one(_FakeS3(), bronze_row, "storyboard-v1")

    assert result.analyzed is False
    assert result.scenes == []
    assert ("quarantine", "video_storyboard", 2) in writes


def test_storyboard_flattens_to_one_row_per_scene_with_video_level_fields(
    monkeypatch: pytest.MonkeyPatch, stub_tables
):
    stub_tables(bronze=_BRONZE_ROWS, silver=None)
    monkeypatch.setattr(a, "analyze_video", lambda path, **kw: _STORYBOARD)

    results, _ = a.analyze_top_videos(limit=1)

    scenes = results[0].scenes
    assert len(scenes) == 2
    assert {s["scene_no"] for s in scenes} == {0, 1}
    assert all(s["hook"] == "Grab attention fast" for s in scenes)
    assert all(s["prompt_version"] == "storyboard-v1" for s in scenes)


def test_limit_bounds_new_videos_not_already_analyzed_ones(
    monkeypatch: pytest.MonkeyPatch, stub_tables
):
    """limit=1 with one video already skipped must still analyze one new video."""
    stub_tables(
        bronze=_BRONZE_ROWS,
        silver=[{
            "video_id": "v2", "prompt_version": "storyboard-v1", "scene_no": 0,
            "t_start": 0.0, "t_end": 1.0, "shot_type": "x", "visual": "x",
            "on_screen_text": "", "voiceover": "", "hook": "h", "cta": "c", "summary": "s",
        }],
    )
    monkeypatch.setattr(a, "analyze_video", lambda path, **kw: _STORYBOARD)

    results, skipped = a.analyze_top_videos(limit=1)

    assert skipped == 1
    assert [r.video_id for r in results] == ["v1"]


def test_render_markdown_includes_hook_scenes_and_cta():
    result = a.AnalyzeResult(
        "v1", _BRONZE_ROWS[0], scenes=[], storyboard=_STORYBOARD, analyzed=True,
    )
    md = a.render_markdown([result])

    assert "Grab attention fast" in md
    assert "Buy now" in md
    assert "hands holding shaver" in md
    assert "using shaver" in md
    assert "Beauty" in md
    assert "1,000 views" in md


def test_render_markdown_skips_unanalyzed_results():
    failed = a.AnalyzeResult("v1", _BRONZE_ROWS[0], scenes=[], storyboard=None, analyzed=False)
    assert a.render_markdown([failed]) == ""


def test_write_silver_quarantines_a_scene_that_fails_the_contract(monkeypatch: pytest.MonkeyPatch):
    good_scene = {
        "video_id": "v1", "prompt_version": "storyboard-v1", "scene_no": 0,
        "t_start": 0.0, "t_end": 1.0, "shot_type": "close-up", "visual": "a hand",
        "on_screen_text": "", "voiceover": "hi", "hook": "h", "hook_style": "hs",
        "cta": "c", "summary": "s",
    }
    bad_scene = {**good_scene, "scene_no": 1, "visual": ""}  # contract requires non-empty
    result = a.AnalyzeResult("v1", _BRONZE_ROWS[0], scenes=[good_scene, bad_scene],
                              storyboard=_STORYBOARD, analyzed=True)

    writes: list[tuple[str, str, int]] = []
    monkeypatch.setattr(
        a, "write_delta",
        lambda layer, name, table, **kw: writes.append((layer, name, table.num_rows)) or 7,
    )

    version = a._write_silver([result])

    assert version == 7
    assert ("quarantine", "video_storyboard", 1) in writes
    assert ("silver", "video_storyboard", 1) in writes


def test_write_silver_is_a_noop_when_nothing_analyzed():
    unanalyzed = a.AnalyzeResult("v1", _BRONZE_ROWS[0], scenes=[], storyboard=None, analyzed=False)
    assert a._write_silver([unanalyzed]) is None
