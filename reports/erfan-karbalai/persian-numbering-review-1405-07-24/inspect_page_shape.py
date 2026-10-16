from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET

root = Path(__file__).resolve().parent
docx = next(p for p in root.glob("*.docx") if not p.name.startswith("~$"))
with ZipFile(docx) as zf:
    tree = ET.fromstring(zf.read("word/document.xml"))
for el in tree.xpath("//*[local-name()='docPr' and starts-with(@name, 'PersianPageNumber_')]")[:3]:
    parent = el
    while parent.getparent() is not None and parent.tag.split('}')[-1] not in {'anchor', 'inline'}:
        parent = parent.getparent()
    print("NAME", el.get("name"))
    print("TEXT", parent.xpath(".//*[local-name()='t']/text()"))
    print("COLORS", [(x.tag.split('}')[-1], dict(x.attrib)) for x in parent.xpath(".//*[local-name()='solidFill']/*")])
    print("BODYPR", [(x.tag.split('}')[-1], dict(x.attrib)) for x in parent.xpath(".//*[local-name()='bodyPr']")])
