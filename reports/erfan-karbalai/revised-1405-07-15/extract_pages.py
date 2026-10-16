from pathlib import Path
from pypdf import PdfReader

root = Path(__file__).resolve().parent
pdf = next(p for p in root.glob("*.pdf") if p.name.startswith("گزارش_"))
reader = PdfReader(str(pdf))
out = root / "page-texts"
out.mkdir(exist_ok=True)
for number, page in enumerate(reader.pages, 1):
    try:
        text = page.extract_text(extraction_mode="layout") or ""
    except KeyError:
        text = ""
    (out / f"page-{number:02d}.txt").write_text(text, encoding="utf-8")
print(f"EXTRACTED={len(reader.pages)}")
