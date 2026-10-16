from pathlib import Path
from docx import Document
import sys
sys.stdout.reconfigure(encoding="utf-8")
root=Path(__file__).resolve().parents[1];d=Document(next(root.glob("*بازبینی‌شده.docx")))
for i,p in enumerate(d.paragraphs):
 if "شکل" in p.text: print(i,p.style.name,repr(p.text))
