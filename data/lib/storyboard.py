"""Render a chunk's storyboard metadata into one LLM-facing reference block.

One renderer, two callers: ``scripts/kalodata_analyze_videos.py``'s
``render_markdown`` (a human-facing preview file) and ``api.py``'s trending
endpoint (a machine-facing ``text`` field) both need the same "what does
this video actually do" block -- diverging them would mean fixing hook/CTA
wording in two places.
"""

from __future__ import annotations

from typing import Any


def render_block(meta: dict[str, Any]) -> str:
    """Render one video's chunk metadata as a prompt-ready reference block.

    Args:
        meta: A chunk's ``metadata`` dict, the shape
            :func:`scripts.index_storyboards.build_chunks` writes --
            ``category_name``, ``revenue``, ``views``, ``ai_video``, ``ad``,
            ``duration_s``, and a nested ``storyboard`` (``hook``, ``cta``,
            ``summary``, ``scenes``).

    Returns:
        A Markdown block: category, revenue/views/kind/duration header,
        the hook, a scene-by-scene table, and the CTA. Empty string if
        there is no storyboard to render.
    """
    storyboard = meta.get("storyboard") or {}
    scenes = storyboard.get("scenes") or []
    if not scenes:
        return ""

    category = meta.get("category_name") or "Unknown"
    revenue = meta.get("revenue") or 0
    views = meta.get("views") or 0
    duration_s = meta.get("duration_s")
    origin = "AI-generated" if meta.get("ai_video") else "human-shot"
    spend = "paid ad" if meta.get("ad") else "organic post"
    duration = f"{duration_s:.0f}s" if duration_s is not None else "duration unknown"

    rows = "\n".join(
        f"| {s['scene_no']} | {s['t_start']:.0f}s | {s['shot_type']} | {s['visual']} | "
        f"{s['on_screen_text']} | {s['voiceover']} |"
        for s in scenes
    )
    return (
        f"## Trending reference — {category}\n"
        f"Revenue ${revenue:,.0f} (USD, last 30d) · {views:,} views (last 30d) · "
        f"{origin} · {spend} · {duration}\n\n"
        f"HOOK: {storyboard.get('hook', '')}\n\n"
        "| # | time | shot | visual | on-screen text | voiceover |\n"
        "|---|------|------|--------|----------------|-----------|\n"
        f"{rows}\n\n"
        f"CTA: {storyboard.get('cta', '')}"
    )
