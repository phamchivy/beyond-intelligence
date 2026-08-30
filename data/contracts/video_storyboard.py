"""Contract for scene-by-scene video storyboards -- sourced from lib/gemini.py."""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series

CONTRACT_VERSION = "video_storyboard-v2"


class VideoStoryboardSchema(pa.DataFrameModel):
    """Silver-layer contract for `video_storyboard`, one row per scene.

    ``hook_style`` is nullable: rows written under ``storyboard-v1`` (before
    this column existed) are still valid, just without it.
    """

    video_id: Series[str]
    prompt_version: Series[str]
    scene_no: Series[int] = pa.Field(ge=0)
    t_start: Series[float] = pa.Field(ge=0.0)
    t_end: Series[float] = pa.Field(ge=0.0)
    shot_type: Series[str]
    visual: Series[str] = pa.Field(str_length=(1, None))
    on_screen_text: Series[str]
    voiceover: Series[str]
    hook: Series[str]
    hook_style: Series[str] = pa.Field(nullable=True)
    cta: Series[str]
    summary: Series[str]
