from pathlib import Path
from collections import Counter

root = Path(__file__).resolve().parent
counts = Counter()
for line in (root / "paragraph-map.tsv").read_text(encoding="utf-8-sig").splitlines():
    parts = line.split("\t", 2)
    if len(parts) == 3:
        try:
            counts[int(parts[0])] += 1
        except ValueError:
            pass
print("EMPTY", [p for p in range(1, 81) if counts[p] == 0])
print("CONTENT", [p for p in range(11, 79) if counts[p] > 0])
