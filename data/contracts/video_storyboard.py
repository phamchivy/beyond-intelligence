"""Contract for scene-by-scene video storyboards -- sourced from lib/gemini.py."""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series

CONTRACT_VERSION = "video_storyboard-v1"


class VideoStoryboardSchema(pa.DataFrameModel):
    """Silver-layer contract for `video_storyboard`, one row per scene."""

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
    cta: Series[str]
    summary: Series[str]
