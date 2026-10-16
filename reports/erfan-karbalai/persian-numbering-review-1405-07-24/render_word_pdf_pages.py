from pathlib import Path
import shutil
import subprocess
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent
pdf = next(root.glob("*.pdf"))
out = root / "qa-word"
if out.exists():
    shutil.rmtree(out)
out.mkdir()
prefix = out / "page"
subprocess.run(["pdftoppm", "-png", "-r", "110", str(pdf), str(prefix)], check=True)
pages = sorted(out.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
for start in range(0, len(pages), 4):
    thumbs = []
    for offset, path in enumerate(pages[start:start + 4]):
        im = Image.open(path).convert("RGB")
        im.thumbnail((500, 707))
        canvas = Image.new("RGB", (520, 745), "white")
        canvas.paste(im, ((520 - im.width) // 2, 28))
        ImageDraw.Draw(canvas).text((10, 7), f"Page {start + offset + 1}", fill="black")
        thumbs.append(canvas)
    sheet = Image.new("RGB", (1040, 1490), "#d8d8d8")
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % 2) * 520, (i // 2) * 745))
    sheet.save(out / f"sheet-{start // 4 + 1:02d}.jpg", quality=90)
print(f"PAGES={len(pages)}")
print(f"SHEETS={(len(pages) + 3) // 4}")
