from pathlib import Path
from docx import Document
import sys
sys.stdout.reconfigure(encoding="utf-8")
d=Document(next(Path(__file__).resolve().parents[1].glob("*بازبینی‌شده.docx")))
for i in [7,11,13,22,255,263,559,584,609,610,630,631,632,633,875]:
 p=d.paragraphs[i];print("P",i,repr(p.text))
 for r in p.runs: print(" ",repr(r.text),r.font.name,r.font.size)
