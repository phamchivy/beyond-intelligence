"""Gemini video understanding -- the only module in `data/` allowed to import google.genai.

Uploads a video via the Files API, waits for it to finish processing, then
asks for a scene-by-scene storyboard as typed JSON in one call. No ffmpeg:
Gemini samples frames and hears the audio itself, unlike the frame-extraction
pipeline architecture doc §6.6 originally assumed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from lib.settings import settings

_POLL_INTERVAL_SECONDS = 2.0
_POLL_TIMEOUT_SECONDS = 120.0

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {
            "type": "string",
            "description": (
                "The opening hook's exact words -- quoted verbatim from the "
                "spoken voiceover or, if the opening has no speech, from its "
                "on-screen text. Not a description of the hook."
            ),
        },
        "hook_style": {
            "type": "string",
            "description": "One-sentence description of what the hook does to grab attention",
        },
        "cta": {"type": "string", "description": "The closing call to action, empty if none"},
        "summary": {"type": "string", "description": "One-sentence summary of the selling angle"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_no": {"type": "integer"},
                    "t_start": {"type": "number", "description": "Scene start, seconds"},
                    "t_end": {"type": "number", "description": "Scene end, seconds"},
                    "shot_type": {
                        "type": "string",
                        "description": "e.g. close-up, wide, POV, talking-head",
                    },
                    "visual": {"type": "string", "description": "What is on screen"},
                    "on_screen_text": {
                        "type": "string",
                        "description": "Burned-in text or captions, empty string if none",
                    },
                    "voiceover": {
                        "type": "string",
                        "description": "Spoken script for this scene, empty string if none",
                    },
                },
                "required": [
                    "scene_no", "t_start", "t_end", "shot_type",
                    "visual", "on_screen_text", "voiceover",
                ],
            },
        },
    },
    "required": ["hook", "hook_style", "cta", "summary", "scenes"],
}

_PROMPT_TEMPLATE = (
    "Watch this short-form vertical video (TikTok Shop content) and break it "
    "into a scene-by-scene storyboard. For each scene give its start/end time "
    "in seconds, the shot type, what is visually on screen, any on-screen "
    "text, and the spoken voiceover script. The video is {duration_clause} long -- "
    "no scene's end time may exceed that. Quote the opening hook's exact words "
    "verbatim (from the voiceover, or the on-screen text if the opening is "
    "silent), then separately describe in one sentence what that hook does to "
    "grab attention. Also give the closing call to action and a one-sentence "
    "summary of the selling angle."
)


def _prompt(duration_s: float | None) -> str:
    """Build the analysis prompt, embedding the known duration when available.

    Args:
        duration_s: The video's duration in seconds, from yt-dlp's Bronze
            metadata. ``None`` for a video whose duration wasn't captured.

    Returns:
        The prompt text, its duration clause naming the real length when
        known so Gemini can't invent a scene past the end of the video.
    """
    clause = f"{duration_s:.0f} seconds" if duration_s is not None else "however many seconds it is"
    return _PROMPT_TEMPLATE.format(duration_clause=clause)


def _wait_until_active(client: genai.Client, file: types.File) -> types.File:
    """Poll an uploaded file until it leaves PROCESSING.

    A ``generate_content`` call against a file still processing fails --
    upload returns before Gemini has ingested the video.

    Args:
        client: An authenticated Gemini client.
        file: The just-uploaded file.

    Returns:
        The file once its state is ACTIVE.

    Raises:
        RuntimeError: If the file reaches FAILED, or is still PROCESSING
            after ``_POLL_TIMEOUT_SECONDS``.
    """
    deadline = time.monotonic() + _POLL_TIMEOUT_SECONDS
    while file.state == types.FileState.PROCESSING:
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"Gemini file {file.name} still processing after {_POLL_TIMEOUT_SECONDS}s"
            )
        time.sleep(_POLL_INTERVAL_SECONDS)
        file = client.files.get(name=file.name)
    if file.state == types.FileState.FAILED:
        raise RuntimeError(f"Gemini failed to process uploaded file {file.name}: {file.error}")
    return file


def analyze_video(
    path: str | Path, *, prompt_version: str, duration_s: float | None = None
) -> dict:
    """Return a scene-by-scene storyboard for one local video file.

    Args:
        path: Local path to the downloaded ``.mp4``.
        prompt_version: Not read here -- the caller records it alongside
            the result as the idempotency key (architecture doc §6.6).
            Kept as a required argument so a call site can't forget that
            changing the prompt above means bumping it too.
        duration_s: The video's known duration in seconds, if available.
            Embedded in the prompt so Gemini's scene timestamps can't run
            past the end of the video it's watching.

    Returns:
        A dict matching ``_RESPONSE_SCHEMA``: ``hook``, ``hook_style``,
        ``cta``, ``summary``, ``scenes`` (list of scene dicts).

    Raises:
        RuntimeError: If the API key is unset, the upload never leaves
            PROCESSING, or the model call fails.
    """
    del prompt_version  # caller's bookkeeping only, see docstring
    if not settings.gemini.api_key.get_secret_value():
        raise RuntimeError("GEMINI_API_KEY is unset -- add it to data/.env")

    client = genai.Client(api_key=settings.gemini.api_key.get_secret_value())
    uploaded = client.files.upload(file=str(path))
    try:
        uploaded = _wait_until_active(client, uploaded)
        try:
            response = client.models.generate_content(
                model=settings.gemini.model,
                contents=[
                    types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type),
                    _prompt(duration_s),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=_RESPONSE_SCHEMA,
                ),
            )
        except genai_errors.APIError as exc:
            raise RuntimeError(f"Gemini analyze_video failed: {exc}") from exc
        return json.loads(response.text)
    finally:
        # Files also expire on their own after 48h, but a per-project
        # storage quota is a bad thing to discover mid-demo.
        client.files.delete(name=uploaded.name)
