"""Dump Bronze/Silver Delta tables to CSV for quick inspection.

Run from `data/`::

    python -m scripts.dump_delta_tables
    python -m scripts.dump_delta_tables --out-dir snapshots
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

from lib.delta import read_delta, table_version

_TABLES = [("bronze", "tiktok_video"), ("silver", "video_storyboard")]


def dump_csv(out_dir: Path) -> list[Path]:
    """Write every table in ``_TABLES`` that exists to its own CSV file.

    Args:
        out_dir: Directory to write into, created if missing.

    Returns:
        Paths written, one per existing table (``{layer}_{name}.csv``).
        Empty if no table in ``_TABLES`` has been written yet.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for layer, name in _TABLES:
        if table_version(layer, name) is None:
            continue
        df = pl.from_arrow(read_delta(layer, name))
        path = out_dir / f"{layer}_{name}.csv"
        df.write_csv(path)
        written.append(path)
    return written


def main() -> int:
    """Parse arguments, dump each existing table to its own CSV file."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", default=".", help="directory to write one CSV per table into")
    args = parser.parse_args()

    written = dump_csv(Path(args.out_dir))
    if not written:
        print("nothing to dump -- no Bronze/Silver tables written yet")
        return 0
    for path in written:
        print(f"written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
