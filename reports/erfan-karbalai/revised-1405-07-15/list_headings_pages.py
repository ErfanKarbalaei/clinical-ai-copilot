from pathlib import Path

root = Path(__file__).resolve().parent
for line in (root / "paragraph-map.tsv").read_text(encoding="utf-8-sig").splitlines():
    parts = line.split("\t", 2)
    if len(parts) == 3 and parts[1].lower().startswith("heading"):
        print("\t".join(parts))
