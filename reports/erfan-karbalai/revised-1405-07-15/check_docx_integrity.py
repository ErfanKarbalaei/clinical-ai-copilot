from pathlib import Path
from zipfile import ZipFile
from docx import Document

root = Path(__file__).resolve().parent
docx = next(root.glob("*.docx"))
with ZipFile(docx) as z:
    bad = z.testzip()
    assert bad is None, bad
doc = Document(str(docx))
paras = [p.text for p in doc.paragraphs]
text = "\n".join(paras)
assert "عرفان کربلائی" in text
assert "۱۵ مهر ۱۴۰۵" in text
assert "۱۵ اکتبر ۲۰۲۶" in text
assert "تقدیم" in text and "سپاسگزاری" in text
print(f"DOCX_OK paragraphs={len(paras)} tables={len(doc.tables)} bytes={docx.stat().st_size}")
