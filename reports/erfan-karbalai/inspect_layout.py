from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import json,sys
sys.stdout.reconfigure(encoding='utf-8')
out=Path(__file__).resolve().parent
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(next(out.glob('*.docx'))) as z:
    root=etree.fromstring(z.read('word/document.xml'))
    for p in root.xpath('//w:body/w:p',namespaces=ns)[:55]:
        txt=''.join(p.xpath('.//w:t/text()',namespaces=ns))
        print(txt[:90],[(etree.QName(e).localname,dict(e.attrib)) for e in p.xpath('./w:pPr/*',namespaces=ns)])
    for n in ['word/styles.xml','word/header4.xml','word/header5.xml']:
        if n not in z.namelist():continue
        r=etree.fromstring(z.read(n))
        if n.endswith('styles.xml'):
            for st in r.xpath('//w:style[@w:styleId="Title" or @w:styleId="Heading1"]',namespaces=ns):print(etree.tostring(st,encoding='unicode')[-1800:])
        else:print(n,etree.tostring(r,encoding='unicode')[-1700:])
print((out/'ooxml-audit.json').read_text())
