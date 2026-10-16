from pathlib import Path
import re
import zipfile
from lxml import etree

root = Path(__file__).resolve().parent
docx = next(p for p in root.glob("*.docx") if not p.name.startswith("~$"))
ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
pat = re.compile(r"[A-Za-z][A-Za-z0-9._/-]*(?:[ \u00a0]+[A-Za-z][A-Za-z0-9._/-]*)+")
seen = set()
with zipfile.ZipFile(docx) as zf:
    for name in zf.namelist():
        if not name.startswith("word/") or not name.endswith(".xml"):
            continue
        try:
            tree = etree.fromstring(zf.read(name))
        except Exception:
            continue
        for p in tree.xpath("//w:p", namespaces=ns):
            text = "".join(p.xpath(".//w:t/text()", namespaces=ns))
            if "Clinical" in text or "Google" in text or "Minimum" in text:
                print("PARA", ascii(text))
            text = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)
            for match in pat.finditer(text):
                value = match.group(0)
                if value not in seen:
                    seen.add(value)
                    print(ascii(value))
print(f"COUNT={len(seen)}")
