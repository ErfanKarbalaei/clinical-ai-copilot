from pathlib import Path
from pypdf import PdfReader

root = Path(__file__).resolve().parent
pdf = next(root.glob("*.pdf"))
reader = PdfReader(str(pdf))
print(f"PDF_PAGES={len(reader.pages)}")
print(f"PDF_SIZE={pdf.stat().st_size}")
