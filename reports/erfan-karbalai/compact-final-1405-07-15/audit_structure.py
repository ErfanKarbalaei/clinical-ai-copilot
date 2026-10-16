from pathlib import Path
from docx import Document
import re,sys
sys.stdout.reconfigure(encoding="utf-8")
out=Path(__file__).resolve().parent
d=Document(out/"گزارش_پروژه_کارشناسی_عرفان_کربلائی_خلاصه‌شده.docx")
for i,p in enumerate(d.paragraphs):
 s=p.text.strip()
 if p.style.name=="Heading 1" or s in ("ماه و سال تحویل: ۱۵ مهر ۱۴۰۵ (15 October 2026)","Submission month and year: 15 Mehr 1405 (15 October 2026)") or "عرفان کربلائی" in s:
  print(i,p.style.name,repr(s[:140]))
print("Table count",len(d.tables),"figures/pics",len(d.inline_shapes))
print("API path wraps",[repr(d.tables[7].cell(i,0).text) for i in range(1,len(d.tables[7].rows))])
print("Running header",[repr("".join(x.text or "" for x in s.header._element.xpath(".//w:t"))) for s in d.sections if "پیوست" in "".join(x.text or "" for x in s.header._element.xpath(".//w:t"))])
print("Tables:")
for ti,t in enumerate(d.tables):
 print(ti,[c.text for c in t.rows[0].cells])
print("References:")
for p in d.paragraphs:
 if re.match(r"^\s*\[\s*(?:\u200e)?[۰-۹]+\s*(?:\u200e)?\]",p.text):print(repr(p.text[:60]))
body=[x.text for x in d.paragraphs]
appendix_heads=[p.text for p in d.paragraphs if p.style.name=="Heading 1" and p.text.startswith("پیوست ")]
assert appendix_heads==["پیوست الف. مسیرهای منتخب رابط برنامه‌نویسی (API)","پیوست ب. تنظیمات منتخب اجرا"],appendix_heads
