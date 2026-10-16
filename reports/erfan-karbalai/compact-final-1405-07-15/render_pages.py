from pathlib import Path
import fitz

out = Path(__file__).resolve().parent
pdf = next(out.glob("*.pdf"))
page_dir = out / "qa-pages"
page_dir.mkdir(exist_ok=True)
for old in page_dir.glob("page-*.png"):
    old.unlink()
doc = fitz.open(pdf)
for i, page in enumerate(doc, 1):
    page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False).save(page_dir / f"page-{i:03d}.png")
print(f"PDF pages: {len(doc)}; rendered page images: {len(list(page_dir.glob('page-*.png')))}")
for i, page in enumerate(doc, 1):
    text = page.get_text()
    if "پیوست الف. مسیرهای منتخب رابط" in text or "پیوست ب. تنظیمات منتخب اجرا" in text:
        print(f"Appendix page {i}: {text[:400].replace(chr(10), ' | ')}")
