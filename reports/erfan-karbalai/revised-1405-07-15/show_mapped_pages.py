from pathlib import Path
import sys

root = Path(__file__).resolve().parent
rows = []
for line in (root / "paragraph-map.tsv").read_text(encoding="utf-8-sig").splitlines():
    parts = line.split("\t", 2)
    if len(parts) == 3:
        try:
            rows.append((int(parts[0]), parts[1], parts[2]))
        except ValueError:
            pass
start, end = int(sys.argv[1]), int(sys.argv[2])
for page in range(start, end + 1):
    print(f"\n===== PAGE {page} =====")
    for p, style, text in rows:
        if p == page:
            print(f"[{style}] {text}")
