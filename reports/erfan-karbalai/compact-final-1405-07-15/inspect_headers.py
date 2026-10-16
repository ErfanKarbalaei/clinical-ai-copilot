from pathlib import Path
from docx import Document
import sys
sys.stdout.reconfigure(encoding="utf-8")
d=Document(Path(__file__).resolve().parent/"گزارش_پروژه_کارشناسی_عرفان_کربلائی_خلاصه‌شده.docx")
for i,s in enumerate(d.sections):
 for kind in ("header","first_page_header","even_page_header"):
  h=getattr(s,kind)
  texts="".join(x.text or "" for x in h._element.xpath(".//w:t"))
  instr="".join(x.text or "" for x in h._element.xpath(".//w:instrText"))
  if "پیوست" in texts or instr.strip():
   print("SECTION",i,kind,"linked",h.is_linked_to_previous,"texts",repr(texts),"instr",repr(instr))
