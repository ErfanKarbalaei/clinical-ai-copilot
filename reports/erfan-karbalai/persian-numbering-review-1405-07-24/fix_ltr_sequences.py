from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as ET
import re

root_dir = Path(__file__).resolve().parent
docx_path = next(p for p in root_dir.glob("*.docx") if not p.name.startswith("~$"))
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
CONTROL = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
LTR_SEQUENCE = re.compile(
    r"\(?[A-Za-z][A-Za-z0-9_./:{}\[\]\-+=@?&%#*'`~<>\\]*"
    r"(?:[ \u00a0]+[A-Za-z0-9_./:{}\[\]\-+=@?&%#*'`~<>\\]+)*\)?"
)

def q(tag: str) -> str:
    return W + tag

with ZipFile(docx_path, "r") as archive:
    blobs = {name: archive.read(name) for name in archive.namelist()}

sequence_count = 0
for name, data in list(blobs.items()):
    if not (name == "word/document.xml" or ((name.startswith("word/header") or name.startswith("word/footer")) and name.endswith(".xml"))):
        continue
    root = ET.fromstring(data)
    for paragraph in root.iter(q("p")):
        nodes = list(paragraph.iter(q("t")))
        if not nodes:
            continue
        clean_values = [CONTROL.sub("", node.text or "") for node in nodes]
        joined = "".join(clean_values)
        matches = [m for m in LTR_SEQUENCE.finditer(joined) if re.search(r"[A-Za-z]", m.group(0))]
        if not matches:
            for node, value in zip(nodes, clean_values):
                node.text = value
            continue

        starts = []
        cursor = 0
        for value in clean_values:
            starts.append(cursor)
            cursor += len(value)
        insertions = [[] for _ in nodes]
        for match in matches:
            start, end = match.span()
            first_i = next(i for i, s in enumerate(starts) if s + len(clean_values[i]) > start)
            last_i = max(i for i, s in enumerate(starts) if s < end)
            first_local = start - starts[first_i]
            last_local = end - starts[last_i]
            # LTR Override (rather than a plain embedding) keeps neutral
            # punctuation such as /, {, }, :, and parentheses in technical
            # identifiers in the exact stored order inside an RTL paragraph.
            insertions[first_i].append((first_local, "\u202d"))
            insertions[last_i].append((last_local, "\u202c"))
            sequence_count += 1

        for i, (node, value) in enumerate(zip(nodes, clean_values)):
            for pos, marker in sorted(insertions[i], key=lambda item: item[0], reverse=True):
                value = value[:pos] + marker + value[pos:]
            node.text = value
            if value.startswith((" ", "\u00a0")) or value.endswith((" ", "\u00a0")):
                node.set(XML_SPACE, "preserve")
    blobs[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

temp_path = docx_path.with_suffix(".ltr.tmp.docx")
with ZipFile(temp_path, "w", ZIP_DEFLATED) as archive:
    for name, data in blobs.items():
        archive.writestr(name, data)
temp_path.replace(docx_path)
print(f"LTR_SEQUENCES={sequence_count}")
