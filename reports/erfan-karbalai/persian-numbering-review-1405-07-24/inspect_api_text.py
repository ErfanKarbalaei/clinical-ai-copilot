from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET

docx = next(Path(__file__).parent.glob("*.docx"))
with ZipFile(docx) as z:
    root = ET.fromstring(z.read("word/document.xml"))
for p in root.xpath(".//*[local-name()='p']"):
    text = "".join(p.xpath(".//*[local-name()='t']/text()"))
    if "/api/" in text or "patient_id" in text or "document_id" in text:
        print(text.encode("unicode_escape").decode("ascii"))
