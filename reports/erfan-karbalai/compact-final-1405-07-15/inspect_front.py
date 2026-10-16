from docx import Document
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")
p=Path(__file__).resolve().parent/"گزارش_پروژه_کارشناسی_عرفان_کربلائی_خلاصه‌شده.docx"
d=Document(p)
for i,x in enumerate(d.paragraphs[:55]):
    print(i,repr(x.text),x.style.name,"pagebreak",bool(x._p.xpath(".//w:br[@w:type='page']")),"bidi",[el.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") for el in x._p.xpath("./w:pPr/w:bidi")])
