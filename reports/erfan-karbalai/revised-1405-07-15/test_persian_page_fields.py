from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as ET
import shutil

root = Path(__file__).resolve().parent
src = next(p for p in root.glob("*.docx") if "test" not in p.name)
dst = root / "nested-page-test.docx"
shutil.copy2(src, dst)
NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + NS + "}"
XML = "{http://www.w3.org/XML/1998/namespace}"
digits = "۰۱۲۳۴۵۶۷۸۹"

def run(parent, *, text=None, fld=None, instr=False):
    r = ET.SubElement(parent, W + "r")
    rpr = ET.SubElement(r, W + "rPr")
    rtl = ET.SubElement(rpr, W + "rtl"); rtl.set(W + "val", "1")
    lang = ET.SubElement(rpr, W + "lang"); lang.set(W + "val", "fa-IR"); lang.set(W + "bidi", "fa-IR")
    if fld:
        node = ET.SubElement(r, W + "fldChar"); node.set(W + "fldCharType", fld)
    elif instr:
        node = ET.SubElement(r, W + "instrText"); node.set(XML + "space", "preserve"); node.text = text
    else:
        node = ET.SubElement(r, W + "t"); node.set(XML + "space", "preserve"); node.text = text or ""

def page_field(parent, cached="1"):
    run(parent, fld="begin"); run(parent, text=" PAGE ", instr=True); run(parent, fld="separate"); run(parent, text=cached); run(parent, fld="end")

def mod10_field(parent, cached="1"):
    run(parent, fld="begin"); run(parent, text=" = MOD(", instr=True); page_field(parent, cached); run(parent, text=",10) ", instr=True); run(parent, fld="separate"); run(parent, text=cached); run(parent, fld="end")

def if_map(parent, values, expr_builder, pos=0, cached=""):
    compare, label = values[pos]
    run(parent, fld="begin"); run(parent, text=" IF ", instr=True); expr_builder(parent); run(parent, text=f' {compare} "{label}" ', instr=True)
    if pos + 1 < len(values):
        if_map(parent, values, expr_builder, pos + 1, cached)
    else:
        run(parent, text='""', instr=True)
    run(parent, fld="separate"); run(parent, text=cached); run(parent, fld="end")

tens = [(f"< {n * 10}", digits[n-1]) for n in range(1, 7)] + [("< 70", digits[6])]
ones = [(f"= {n}", digits[n]) for n in range(10)]

with ZipFile(dst) as z:
    blobs = {name: z.read(name) for name in z.namelist()}
changed_count = 0
for name, data in list(blobs.items()):
    if not ((name.startswith("word/footer") or name.startswith("word/header")) and name.endswith(".xml")):
        continue
    node = ET.fromstring(data)
    for p in node.findall(f".//{W}p"):
        instructions = " ".join((x.text or "") for x in p.findall(f".//{W}instrText"))
        if "PAGE" not in instructions:
            continue
        ppr = p.find(W + "pPr")
        for child in list(p):
            if child is not ppr:
                p.remove(child)
        if_map(p, tens, lambda target: page_field(target), cached="")
        if_map(p, ones, lambda target: mod10_field(target), cached="۱")
        changed_count += 1
    blobs[name] = ET.tostring(node, encoding="utf-8", xml_declaration=True)
with ZipFile(dst, "w", ZIP_DEFLATED) as z:
    for name, data in blobs.items():
        z.writestr(name, data)
print(f"CHANGED={changed_count}")
