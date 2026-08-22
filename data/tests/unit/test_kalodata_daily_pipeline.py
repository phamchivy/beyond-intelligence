"""Unit tests for scripts/kalodata_daily_pipeline.py -- every step is a spy.

No network, no S3, no Postgres, no Gemini: this only asserts the
orchestration -- what gets called, in what order, with what results fed
forward -- not any of the underlying logic (that's each step's own tests).
"""

from __future__ import annotations

import pytest

from scripts import kalodata_daily_pipeline as p


class _Result:
    """Stands in for a kalodata_download_videos.FetchResult."""

    def __init__(self, downloaded: bool) -> None:
        self.downloaded = downloaded


class _AnalyzeResult:
    """Stands in for a kalodata_analyze_videos.AnalyzeResult."""

    def __init__(self, analyzed: bool) -> None:
        self.analyzed = analyzed


def test_runs_discover_then_download_per_keyword_then_analyze_once_then_index_once(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[str] = []

    monkeypatch.setattr(p, "discover_keywords", lambda: (calls.append("discover") or ["a", "b"]))

    def _download(keyword: str):
        calls.append(f"download:{keyword}")
        return [_Result(downloaded=True)]

    monkeypatch.setattr(p, "download_top_videos", _download)
    monkeypatch.setattr(p, "_write_bronze", lambda results: calls.append("write_bronze"))
    monkeypatch.setattr(
        p, "analyze_top_videos",
        lambda: (calls.append("analyze") or ([_AnalyzeResult(analyzed=True)], 0)),
    )
    monkeypatch.setattr(p, "_write_silver", lambda results: calls.append("write_silver"))
    monkeypatch.setattr(p.index_storyboards, "main", lambda: calls.append("index"))

    assert p.main() == 0
    assert calls == [
        "discover",
        "download:a", "write_bronze",
        "download:b", "write_bronze",
        "analyze", "write_silver",
        "index",
    ]


def test_a_keyword_that_fails_to_rank_does_not_abort_the_rest(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(p, "discover_keywords", lambda: ["bad", "good"])

    def _download(keyword: str):
        if keyword == "bad":
            raise RuntimeError("KALODATA_API_KEY is unset")
        return [_Result(downloaded=True)]

    monkeypatch.setattr(p, "download_top_videos", _download)
    written: list[str] = []
    monkeypatch.setattr(p, "_write_bronze", lambda results: written.append("bronze"))
    monkeypatch.setattr(p, "analyze_top_videos", lambda: ([], 0))
    monkeypatch.setattr(p, "_write_silver", lambda results: None)
    monkeypatch.setattr(p.index_storyboards, "main", lambda: None)

    assert p.main() == 0
    assert written == ["bronze"]  # only "good" made it to a Bronze write
