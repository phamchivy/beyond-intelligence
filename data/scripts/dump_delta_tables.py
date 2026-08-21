"""Dump Bronze/Silver Delta tables to a markdown file for quick inspection.

Run from `data/`::

    python -m scripts.dump_delta_tables
    python -m scripts.dump_delta_tables --out snapshot.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

from lib.delta import read_delta, table_version

_TABLES = [("bronze", "tiktok_video"), ("silver", "video_storyboard")]


def render_markdown() -> str:
    """Render every table in ``_TABLES`` that exists as a markdown section.

    Returns:
        One ``## layer/name`` section per existing table, each table's
        rows as a fenced code block (polars' own repr -- no pandas/tabulate
        dependency needed for a quick-look dump).
    """
    sections = []
    for layer, name in _TABLES:
        if table_version(layer, name) is None:
            continue
        df = pl.from_arrow(read_delta(layer, name))
        with pl.Config(tbl_rows=-1, tbl_cols=-1, fmt_str_lengths=200, tbl_width_chars=200):
            sections.append(f"## {layer}/{name} ({df.height} rows)\n\n```\n{df}\n```")
    return "\n\n".join(sections)


def main() -> int:
    """Parse arguments, render, write the markdown file."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="delta_snapshot.md", help="output .md path")
    args = parser.parse_args()

    Path(args.out).write_text(render_markdown())
    print(f"written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
