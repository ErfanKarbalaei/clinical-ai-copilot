from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
import sys
sys.stdout.reconfigure(encoding="utf-8")
d=Document(next(Path(__file__).resolve().parents[1].glob("*بازبینی‌شده.docx")))
for i,n in enumerate(d.element.body):
 if n.tag==qn("w:p"):
  p=Paragraph(n,d);t=p.text.strip()
  if i>900 or "پیوست الف" in t:
   br=len(n.xpath(".//w:br[@w:type='page']"))
   print(i,"P",p.style.name,repr(t[:100]),"pbefore",p.paragraph_format.page_break_before,"br",br,"sect",bool(n.xpath(".//w:sectPr")))
 elif n.tag==qn("w:tbl") and i>900: print(i,"TABLE")
 elif n.tag==qn("w:sectPr"): print(i,"SECTPR")
