from pathlib import Path
from PIL import Image, ImageDraw
pages_dir=Path(__file__).resolve().parent/"qa-pages"
pages=sorted(pages_dir.glob("page-*.png"), key=lambda p:int(p.stem.split("-")[-1]))
sheet_dir=pages_dir/"sheets"
sheet_dir.mkdir(exist_ok=True)
thumb_w,thumb_h=390,550
for start in range(0,len(pages),4):
    sheet=Image.new("RGB",(thumb_w*2, (thumb_h+32)*2),(238,238,238))
    draw=ImageDraw.Draw(sheet)
    for j,p in enumerate(pages[start:start+4]):
        im=Image.open(p).convert("RGB")
        im.thumbnail((thumb_w,thumb_h))
        x=(j%2)*thumb_w+(thumb_w-im.width)//2
        y=(j//2)*(thumb_h+32)+24
        sheet.paste(im,(x,y))
        draw.text(((j%2)*thumb_w+8,(j//2)*(thumb_h+32)+5),f"Physical page {start+j+1}",fill=(0,0,0))
    sheet.save(sheet_dir/f"sheet-{start//4+1:02d}.png")
print(f"Rendered page images: {len(pages)}; contact sheets: {len(list(sheet_dir.glob('sheet-*.png')))}")
