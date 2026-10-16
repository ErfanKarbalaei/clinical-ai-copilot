from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET

root = Path(__file__).resolve().parent
docx = next(p for p in root.glob("*.docx") if not p.name.startswith("~$"))
ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
with ZipFile(docx) as zf:
    for name in zf.namelist():
        if (name.startswith("word/header") or name.startswith("word/footer")) and name.endswith(".xml"):
            tree = ET.fromstring(zf.read(name))
            text = "|".join(tree.xpath("//w:t/text()", namespaces=ns))
            print(name, ascii(text))
