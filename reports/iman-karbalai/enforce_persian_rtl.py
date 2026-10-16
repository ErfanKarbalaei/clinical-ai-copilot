from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{NS}}}"
ASCII_TO_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
def child(parent: etree._Element, local: str) -> etree._Element:
    node = parent.find(W + local)
    if node is None:
        node = etree.Element(W + local)
        parent.insert(0, node)
    return node


def set_val(parent: etree._Element, local: str, value: str) -> None:
    node = child(parent, local)
    node.set(W + "val", value)


def enforce(docx: Path) -> None:
    with ZipFile(docx) as package:
        parts = {item.filename: package.read(item.filename) for item in package.infolist()}

    xml_parts = [
        name
        for name in parts
        if name == "word/document.xml"
        or name.startswith("word/header") and name.endswith(".xml")
        or name.startswith("word/footer") and name.endswith(".xml")
    ]
    for name in xml_parts:
        root = etree.fromstring(parts[name])
        for paragraph in root.iter(W + "p"):
            ppr = child(paragraph, "pPr")
            set_val(ppr, "bidi", "1")
            set_val(ppr, "jc", "start")
            style = ppr.find(W + "pStyle")
            style_name = style.get(W + "val", "") if style is not None else ""
            convert_digits = (
                name.startswith("word/header")
                or name.startswith("word/footer")
                or style_name.startswith("TOC")
                or style_name.startswith("Heading")
            )
            if convert_digits:
                for text_node in paragraph.iter(W + "t"):
                    if text_node.text:
                        text_node.text = text_node.text.translate(ASCII_TO_FA)
        for run in root.iter(W + "r"):
            rpr = child(run, "rPr")
            set_val(rpr, "rtl", "1")
            lang = child(rpr, "lang")
            if lang.get(W + "val") is None:
                lang.set(W + "val", "fa-IR")
            lang.set(W + "bidi", "fa-IR")
        for table in root.iter(W + "tbl"):
            tblpr = child(table, "tblPr")
            set_val(tblpr, "bidiVisual", "1")
            set_val(tblpr, "jc", "right")
        parts[name] = etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", standalone=True
        )

    temp = docx.with_suffix(".rtl.tmp.docx")
    with ZipFile(temp, "w", ZIP_DEFLATED) as package:
        for name, data in parts.items():
            package.writestr(name, data)
    temp.replace(docx)


if __name__ == "__main__":
    target = Path(sys.argv[1])
    enforce(target)
    print("RTL properties applied")
