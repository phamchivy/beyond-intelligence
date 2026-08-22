"""Generate tests/fixtures/policy.pdf: a short TikTok-Shop-style ad policy document with a table.

Run once: `python scripts/generate_fixture_pdf.py`. Dev-only tool --
reportlab is not a runtime dependency of the pipeline itself, only of
producing this one fixture.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "policy.pdf"

_SECTIONS = [
    ("1. Pham vi ap dung",
     "Chinh sach nay ap dung cho toan bo noi dung quang cao va livestream ban hang "
     "tren nen tang TikTok Shop, bao gom video quang cao, hinh anh san pham va mo ta san pham."),
    ("2. Chinh sach quang cao my pham",
     "Quang cao my pham khong duoc phep dua ra cam ket dieu tri benh ly, khong su dung "
     "hinh anh truoc/sau gay hieu lam, va phai cong khai thanh phan chinh cua san pham. "
     "Moi noi dung 'giam gia' phai neu ro thoi han va dieu kien ap dung."),
    ("3. Muc phat vi pham",
     "Vi pham lan dau bi canh cao va go noi dung. Vi pham lap lai trong 30 ngay dan den "
     "tam khoa kenh 7 ngay. Vi pham nghiem trong (quang cao san pham cam) dan den khoa "
     "kenh vinh vien."),
    ("4. Quy trinh khieu nai",
     "Nguoi ban co the khieu nai quyet dinh trong vong 14 ngay ke tu ngay nhan thong bao, "
     "thong qua muc Ho tro nguoi ban trong ung dung TikTok Shop Seller Center."),
]

_TABLE_DATA = [
    ["Muc vi pham", "Lan 1", "Lan 2 (30 ngay)", "Nghiem trong"],
    ["Canh bao", "Co", "Khong", "Khong"],
    ["Go noi dung", "Co", "Co", "Co"],
    ["Tam khoa kenh", "Khong", "7 ngay", "Khong"],
    ["Khoa kenh vinh vien", "Khong", "Khong", "Co"],
]


def generate() -> None:
    """Write the fixture PDF to tests/fixtures/policy.pdf."""
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(_OUT), pagesize=A4)
    story = [Paragraph("Chinh sach quang cao TikTok Shop", styles["Title"]), Spacer(1, 1 * cm)]

    for heading, body in _SECTIONS:
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(Paragraph(body, styles["BodyText"]))
        story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Bang muc phat theo so lan vi pham", styles["Heading2"]))
    table = Table(_TABLE_DATA)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)

    doc.build(story)
    print(f"wrote {_OUT}")


if __name__ == "__main__":
    generate()
