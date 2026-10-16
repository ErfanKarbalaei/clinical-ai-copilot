from pathlib import Path
import fitz

pdf = next(Path(__file__).parent.glob("*.pdf"))
doc = fitz.open(pdf)
for i, page in enumerate(doc, 1):
    text = page.get_text()
    if "/api/" in text or "patient_id" in text or "document_id" in text:
        print(i)
