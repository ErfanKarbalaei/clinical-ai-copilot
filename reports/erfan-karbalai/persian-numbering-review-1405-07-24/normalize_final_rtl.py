from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as ET
import re

root_dir = Path(__file__).resolve().parent
docx_path = next(root_dir.glob("*.docx"))
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LTR = re.compile(r"[A-Za-z][A-Za-z0-9_.:/{}?=+\-]*")

def q(tag):
    return W + tag

with ZipFile(docx_path, "r") as archive:
    blobs = {name: archive.read(name) for name in archive.namelist()}

styles = ET.fromstring(blobs["word/styles.xml"])
centered_styles = set()
numbered_styles = set()
for style in styles.iter(q("style")):
    style_id = style.get(q("styleId"))
    name_node = style.find(q("name"))
    style_name = (name_node.get(q("val")) if name_node is not None else "").lower()
    justification = style.find(f"{q('pPr')}/{q('jc')}")
    if style_id and justification is not None and justification.get(q("val")) == "center":
        centered_styles.add(style_id)
    if style_id and (style_id.lower().startswith(("toc", "heading")) or style_id.lower() in {"reportfigure", "reporttable"} or style_name.startswith(("toc", "heading")) or style_name in {"reportfigure", "reporttable"}):
        numbered_styles.add(style_id)

for name, data in list(blobs.items()):
    if not (name == "word/document.xml" or ((name.startswith("word/header") or name.startswith("word/footer")) and name.endswith(".xml"))):
        continue
    root = ET.fromstring(data)
    for paragraph in root.iter(q("p")):
        ppr = paragraph.find(q("pPr"))
        if ppr is None:
            ppr = ET.Element(q("pPr"))
            paragraph.insert(0, ppr)
        old_jc = ppr.find(q("jc"))
        style = ppr.find(q("pStyle"))
        style_id = style.get(q("val")) if style is not None else ""
        was_centered = ((old_jc is not None and old_jc.get(q("val")) == "center") or
                        (style is not None and style.get(q("val")) in centered_styles))
        if old_jc is None:
            old_jc = ET.SubElement(ppr, q("jc"))
        old_jc.set(q("val"), "start")
        bidi = ppr.find(q("bidi"))
        if bidi is None:
            bidi = ET.SubElement(ppr, q("bidi"))
        bidi.set(q("val"), "1")
        # Word text boxes used for the static Persian page numbers are only a
        # few points wide.  Adding the document-wide centre tab to those
        # paragraphs pushes their text outside the box and makes the number
        # disappear in Word/PDF rendering.  Keep the explicit RTL/start
        # properties, but do not insert the body-layout tab in text boxes.
        inside_text_box = any(
            ancestor.tag in {q("txbxContent"), "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}txbx"}
            for ancestor in paragraph.iterancestors()
        )
        if was_centered and not inside_text_box:
            tabs = ppr.find(q("tabs"))
            if tabs is None:
                tabs = ET.SubElement(ppr, q("tabs"))
            if not any(tab.get(q("val")) == "center" for tab in tabs.findall(q("tab"))):
                tab = ET.SubElement(tabs, q("tab"))
                tab.set(q("val"), "center")
                tab.set(q("pos"), "4536")
            runs = paragraph.findall(q("r"))
            if runs and runs[0].find(q("tab")) is None:
                tab_run = ET.Element(q("r"))
                rpr = ET.SubElement(tab_run, q("rPr"))
                rtl = ET.SubElement(rpr, q("rtl")); rtl.set(q("val"), "1")
                ET.SubElement(tab_run, q("tab"))
                paragraph.insert(list(paragraph).index(runs[0]), tab_run)
        for text_run in paragraph.iter(q("r")):
            texts = list(text_run.iter(q("t")))
            if not texts:
                continue
            rpr = text_run.find(q("rPr"))
            if rpr is None:
                rpr = ET.Element(q("rPr"))
                text_run.insert(0, rpr)
            rtl = rpr.find(q("rtl"))
            if rtl is None:
                rtl = ET.SubElement(rpr, q("rtl"))
            rtl.set(q("val"), "1")
            lang = rpr.find(q("lang"))
            if lang is None:
                lang = ET.SubElement(rpr, q("lang"))
            lang.set(q("val"), "fa-IR")
            lang.set(q("bidi"), "fa-IR")
            for text in texts:
                value = text.text or ""
                if style_id in numbered_styles:
                    value = value.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                    text.text = value
                if re.search(r"[A-Za-z]", value) and "\u202a" not in value:
                    text.text = LTR.sub(lambda match: "\u202a" + match.group(0) + "\u202c", value)
    for table in root.iter(q("tbl")):
        table_properties = table.find(q("tblPr"))
        if table_properties is None:
            table_properties = ET.Element(q("tblPr"))
            table.insert(0, table_properties)
        bidi_visual = table_properties.find(q("bidiVisual"))
        if bidi_visual is None:
            bidi_visual = ET.SubElement(table_properties, q("bidiVisual"))
        bidi_visual.set(q("val"), "1")
    blobs[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

temp_path = docx_path.with_suffix(".rtl.tmp.docx")
with ZipFile(temp_path, "w", ZIP_DEFLATED) as archive:
    for name, data in blobs.items():
        archive.writestr(name, data)
temp_path.replace(docx_path)
print("RTL_NORMALIZED")
