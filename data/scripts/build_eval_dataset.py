"""Build evaluation/datasets/retrieval.jsonl from hand-written queries against the live index.

Run after stage 4 (`silver_document_chunk` materialized, so the policy PDF
is indexed), from `data/`: `python -m scripts.build_eval_dataset`. The queries and their
intended matching substring are hand-written and reviewed below; only the
resulting chunk ids are looked up mechanically, because Docling's chunk
boundaries are not something a human can predict by hand. The output file
is still committed to git and reviewed like any other label.

Three deliberate families, matching the reasoning in data-architecture.md
§10 and §12: an exact-identifier query (dense retrieval alone struggles),
a paraphrase (lexical retrieval alone struggles), and a
diacritic-stripped Vietnamese query (proves the pg_trgm + unaccent
mitigation).
"""

from __future__ import annotations

import json
from pathlib import Path

from lib import db

_OUT = Path(__file__).resolve().parent.parent / "evaluation" / "datasets" / "retrieval.jsonl"

# (query, substring expected to appear in the matching chunk's content, language)
_CASES: list[tuple[str, str, str]] = [
    ("chinh sach quang cao my pham", "my pham", "vi"),          # diacritic-stripped
    ("chính sách quảng cáo mỹ phẩm", "my pham", "vi"),           # same, with diacritics
    ("muc phat vi pham lan dau", "canh bao", "vi"),               # paraphrase of section 3
    ("quy trinh khieu nai 14 ngay", "khieu nai", "vi"),           # exact detail (14 ngay)
    ("dieu kien giam gia quang cao", "giam gia", "vi"),
    ("khoa kenh vinh vien", "khoa kenh vinh vien", "vi"),
    ("pham vi ap dung chinh sach", "pham vi ap dung", "vi"),
    ("TikTok Shop Seller Center", "seller center", "vi"),
]


def _find_expected_chunk_ids(substring: str) -> list[str]:
    """Look up chunk ids whose content contains the given substring, case-insensitive."""
    with db.connection() as conn:
        rows = conn.execute(
            'select chunk_id from "index".chunk where lower(content) like %s',
            (f"%{substring.lower()}%",),
        ).fetchall()
    return [r["chunk_id"] for r in rows]


def build() -> None:
    """Write the labeled dataset by resolving each hand-written case against the live index."""
    cases = []
    for i, (query, substring, lang) in enumerate(_CASES, start=1):
        expected = _find_expected_chunk_ids(substring)
        if not expected:
            print(f"WARNING: no chunk found for case q{i:03d} ({query!r}) -- skipping")
            continue
        cases.append({
            "case_id": f"q{i:03d}", "query": query, "expected_chunk_ids": expected, "lang": lang,
        })

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    with _OUT.open("w") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    print(f"wrote {len(cases)} cases to {_OUT}")


if __name__ == "__main__":
    build()
