from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as ET
import shutil

root = Path(__file__).resolve().parent
src = next(root.glob("*.docx"))
dst = root / "fieldformat-test.docx"
shutil.copy2(src, dst)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
with ZipFile(dst) as z:
    blobs = {name: z.read(name) for name in z.namelist()}
for name, data in list(blobs.items()):
    if (name.startswith("word/footer") or name.startswith("word/header")) and name.endswith(".xml"):
        node = ET.fromstring(data)
        changed = False
        for instr in node.findall(f".//{W}instrText"):
            if (instr.text or "").strip() == "PAGE":
                instr.text = ' PAGE \\# "۰" '
                changed = True
        if changed:
            blobs[name] = ET.tostring(node, encoding="utf-8", xml_declaration=True)
with ZipFile(dst, "w", ZIP_DEFLATED) as z:
    for name, data in blobs.items():
        z.writestr(name, data)
print("OK")
