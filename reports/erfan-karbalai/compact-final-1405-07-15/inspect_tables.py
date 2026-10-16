from pathlib import Path
from docx import Document
import sys
sys.stdout.reconfigure(encoding="utf-8")
d=Document(next(Path(__file__).resolve().parents[1].glob("*بازبینی‌شده.docx")))
for t in d.tables[:4]:
 print(t.style.name, t._tbl.tblPr.xml[:600])
