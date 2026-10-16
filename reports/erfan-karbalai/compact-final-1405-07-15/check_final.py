from pathlib import Path
import re, zipfile, sys
from docx import Document
sys.stdout.reconfigure(encoding="utf-8")

out = Path(__file__).resolve().parent
docx = next(out.glob("*.docx"))
with zipfile.ZipFile(docx) as z:
    assert z.testzip() is None
d = Document(docx)
all_paras = [p.text for p in d.paragraphs]
all_cells = [c.text for t in d.tables for row in t.rows for c in row.cells]
clean = lambda s: re.sub(r"[\u200e\u200f\u202a\u202c\u2066\u2069]", "", s)
all_text = "\n".join(clean(x) for x in all_paras + all_cells)
assert "عرفان کربلائی" in all_text
assert "عرفان کربالئی" not in all_text
assert "۱۵ مهر ۱۴۰۵ (۱۵ اکتبر ۲۰۲۶)" in all_text
assert "۱۵ اکتبر ۲۰۲۶" not in all_text or "۱۵ مهر ۱۴۰۵" in all_text
assert "پیوست الف. مسیرهای منتخب رابط برنامه‌نویسی (API)" in all_text
assert "پیوست ب. تنظیمات منتخب اجرا" in all_text
assert not any(f"[{n}]" in all_text for n in (11, 12, 13, 14))
refs = [clean(p.text).strip() for p in d.paragraphs if re.match(r"^\[\s*[۰-۹0-9]+\s*\]", clean(p.text).strip())]
digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
ref_nums = [int(re.search(r"\d+", x.translate(digits)).group()) for x in refs]
assert ref_nums == list(range(1, 11)), ref_nums
print("DOCX ZIP: valid")
print("Author/date: exact Persian spelling and requested date present")
print("Bibliography numbering:", ref_nums)
print("Tables:", len(d.tables), "inline images:", len(d.inline_shapes))
print("Appendices:", [p.text for p in d.paragraphs if p.style.name == "Heading 1" and p.text.startswith("پیوست ")])
print("Docx bytes:", docx.stat().st_size)
print("PDF bytes:", next(out.glob("*.pdf")).stat().st_size)
