from pathlib import Path
from PIL import Image, ImageChops

root = Path(__file__).resolve().parent
old = root / "qa-pages" / "normalized"
new = root / "qa-final"
old_pages = sorted(old.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
new_pages = sorted(new.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
assert len(old_pages) == len(new_pages) == 80, (len(old_pages), len(new_pages))
diffs = []
for a, b in zip(old_pages, new_pages):
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size or ImageChops.difference(ia, ib).getbbox():
        diffs.append((a.name, ia.size, ib.size))
print(f"Compared {len(old_pages)} page images; differing pages: {diffs}")
