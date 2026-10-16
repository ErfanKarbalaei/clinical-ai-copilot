from pathlib import Path
from collections import defaultdict
import re

source = Path(__file__).resolve().parents[1] / "revised-1405-07-15" / "paragraph-map.tsv"
output = Path(__file__).resolve().parent / "page-anchors.tsv"
rows = defaultdict(list)
for line in source.read_text(encoding="utf-8-sig").splitlines():
    parts = line.split("\t", 2)
    if len(parts) != 3:
        continue
    try:
        page = int(parts[0])
    except ValueError:
        continue
    rows[page].append((parts[1], parts[2].strip()))

skip = {20, 34, 48, 54, 60, 70, 74}
front_overrides = {
    11: "فهرست مطالب",
    12: "۴-۷. خطا و یکپارچگی عملیات",
    13: "فصل هشتم صوت و تبدیل گفتار به متن",
    14: "فصل یازدهم آزمون یکپارچه‌سازی و استقرار",
    15: "فهرست شکل‌ها",
    16: "فهرست جدول‌ها",
}
lines = []
for page in range(11, 79):
    if page in skip:
        continue
    if page in front_overrides:
        lines.append(f"{page}\t{front_overrides[page]}")
        continue
    candidates = [(style, text) for style, text in rows[page] if len(text) >= 12 and text != "/"]
    if not candidates:
        raise RuntimeError(f"No anchor for page {page}")
    style, text = candidates[0]
    text = re.sub(r"\s+[0-9]+$", "", text)
    snippet = text[:56].replace("\t", " ").replace("\r", " ").replace("\n", " ")
    lines.append(f"{page}\t{snippet}")
output.write_text("\ufeff" + "\n".join(lines) + "\n", encoding="utf-8")
print(f"ANCHORS={len(lines)}")
