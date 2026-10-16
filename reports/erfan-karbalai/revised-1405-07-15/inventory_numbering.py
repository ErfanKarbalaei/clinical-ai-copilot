from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET
from docx import Document
import re

root = Path(__file__).resolve().parent
docx_path = next(root.glob("*.docx"))
doc = Document(str(docx_path))

digit_re = re.compile(r"[0-9۰-۹٠-٩]")
for i, p in enumerate(doc.paragraphs):
    style = p.style.name if p.style else ""
    text = p.text.strip()
    if text and (style.startswith("Heading") or "عنوان" in style or re.match(r"^[فپ]صل", text) or re.match(r"^[0-9۰-۹٠-٩]+[-ـ.][0-9۰-۹٠-٩]+", text)):
        print(f"P{i}\t{style}\t{text}")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
with ZipFile(docx_path) as z:
    for name in sorted(n for n in z.namelist() if n.startswith("word/footer") and n.endswith(".xml")):
        root_xml = ET.fromstring(z.read(name))
        text = "".join(root_xml.itertext()).strip()
        if text or root_xml.findall(f".//{W}fldSimple") or root_xml.findall(f".//{W}instrText"):
            print("FOOTER", name, repr(text))
            for instr in root_xml.findall(f".//{W}instrText"):
                print(" FIELD", repr(instr.text))
