from pathlib import Path
import subprocess
from PIL import Image, ImageOps, ImageDraw

root = Path(__file__).resolve().parent
out = root / "qa-final"
out.mkdir(exist_ok=True)
pdf = next(root.glob("*.pdf"))
prefix = out / "page"
subprocess.run(["pdftoppm", "-png", "-r", "90", str(pdf), str(prefix)], check=True)
pages = sorted(out.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
for start in range(0, len(pages), 4):
    thumbs = []
    for path in pages[start:start + 4]:
        im = Image.open(path).convert("RGB")
        im.thumbnail((375, 530))
        canvas = Image.new("RGB", (390, 560), "white")
        canvas.paste(im, ((390-im.width)//2, 26))
        ImageDraw.Draw(canvas).text((8, 5), f"Page {start + len(thumbs) + 1}", fill="black")
        thumbs.append(canvas)
    sheet = Image.new("RGB", (780, 1120), "#ddd")
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % 2) * 390, (i // 2) * 560))
    sheet.save(out / f"sheet-{start//4+1:02d}.png")
print(f"Rendered {len(pages)} pages to {out}")
