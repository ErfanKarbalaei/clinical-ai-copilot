from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET
from pypdf import PdfReader
import re

root = Path(__file__).resolve().parent
docx = next(p for p in root.glob("*.docx") if not p.name.startswith("~$"))
pdf = next(root.glob("*.pdf"))
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"

def q(tag):
    return W + tag

def pdigits(value):
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

with ZipFile(docx) as zf:
    blobs = {name: zf.read(name) for name in zf.namelist()}

styles = ET.fromstring(blobs["word/styles.xml"])
numbered_styles = set()
for style in styles.iter(q("style")):
    sid = style.get(q("styleId"), "")
    name = style.find(q("name"))
    sname = (name.get(q("val"), "") if name is not None else "").lower()
    if sid.lower().startswith(("heading", "toc")) or sname.startswith(("heading", "toc")):
        numbered_styles.add(sid)

doc = ET.fromstring(blobs["word/document.xml"])
shape_map = {}
for docpr in doc.iter(WP + "docPr"):
    name = docpr.get("name", "")
    match = re.fullmatch(r"PersianPageNumber_(\d+)", name)
    if not match:
        continue
    physical = int(match.group(1))
    ancestor = docpr
    while ancestor.getparent() is not None and ancestor.tag != q("drawing"):
        ancestor = ancestor.getparent()
    drawing = ancestor if ancestor.tag == q("drawing") else docpr.getparent()
    text = "".join(drawing.xpath(".//w:t/text()", namespaces={"w": W[1:-1]}))
    shape_map[physical] = text

expected_pages = [p for p in range(11, 79) if p not in {20, 34, 48, 54, 60, 70, 74}]
shape_errors = []
for physical in expected_pages:
    expected = pdigits(physical - 10)
    if shape_map.get(physical) != expected:
        shape_errors.append((physical, shape_map.get(physical), expected))

ascii_numbered = []
for p in doc.iter(q("p")):
    style = p.find(f"{q('pPr')}/{q('pStyle')}")
    sid = style.get(q("val"), "") if style is not None else ""
    if sid in numbered_styles:
        text = "".join(p.xpath(".//w:t/text()", namespaces={"w": W[1:-1]}))
        if re.search(r"[0-9]", text):
            ascii_numbered.append((sid, text[:120]))

field_text = "\n".join(
    data.decode("utf-8", errors="ignore")
    for name, data in blobs.items()
    if name.startswith("word/") and name.endswith(".xml")
)
page_fields = len(re.findall(r"\bPAGE\b", field_text))
pdf_pages = len(PdfReader(str(pdf)).pages)
raw_shape_names = sorted(set(int(x) for x in re.findall(r"PersianPageNumber_(\d+)", blobs["word/document.xml"].decode("utf-8", errors="ignore"))))
static_header_footer_numbers = []
for name, data in blobs.items():
    if not ((name.startswith("word/header") or name.startswith("word/footer")) and name.endswith(".xml")):
        continue
    tree = ET.fromstring(data)
    for p in tree.iter(q("p")):
        text = "".join(p.xpath(".//w:t/text()", namespaces={"w": W[1:-1]})).strip()
        if re.fullmatch(r"[0-9]+", text):
            static_header_footer_numbers.append((name, text))

print(f"PDF_PAGES={pdf_pages}")
print(f"PAGE_NUMBER_SHAPES={len(shape_map)}")
print(f"RAW_PAGE_NUMBER_NAMES={len(raw_shape_names)}")
print(f"RAW_MISSING={sorted(set(expected_pages) - set(raw_shape_names))}")
print(f"PAGE_NUMBER_SHAPE_ERRORS={len(shape_errors)}")
print(f"ASCII_DIGIT_NUMBERED_PARAGRAPHS={len(ascii_numbered)}")
print(f"PAGE_FIELDS={page_fields}")
print(f"STATIC_HEADER_FOOTER_ASCII_NUMBERS={len(static_header_footer_numbers)}")
if shape_errors:
    print(f"SHAPE_ERRORS={shape_errors[:10]}")
if ascii_numbered:
    print(f"ASCII_EXAMPLES={ascii_numbered[:10]}")
if not (pdf_pages == 80 and len(shape_map) == 61 and not shape_errors and not ascii_numbered and page_fields == 0 and not static_header_footer_numbers):
    raise SystemExit(1)
print("VALIDATION_PASS=1")
