from pathlib import Path
from docx import Document
import sys
sys.stdout.reconfigure(encoding='utf-8')
o=Path(__file__).resolve().parent
d=Document(o/'گزارش_پروژه_کارشناسی_عرفان_کربالئی.docx')
for i in [245,246,247]:
    print('PARAGRAPH',i,d.paragraphs[i]._p.xml)
