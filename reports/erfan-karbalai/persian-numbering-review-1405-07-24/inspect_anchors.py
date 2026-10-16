from pathlib import Path

p = Path(__file__).with_name("page-anchors.tsv")
for i, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines()[:8], 1):
    print(i, ascii(line), [hex(ord(ch)) for ch in line[:24]])
