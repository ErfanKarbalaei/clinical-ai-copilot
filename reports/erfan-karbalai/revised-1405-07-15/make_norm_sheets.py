from pathlib import Path
from PIL import Image, ImageDraw
base=Path(__file__).resolve().parent/"qa-pages"/"normalized"
pages=sorted(base.glob("page-*.png"),key=lambda p:int(p.stem.split("-")[-1]))
sheets=base/"sheets";sheets.mkdir(exist_ok=True)
w,h=390,550
for start in range(0,len(pages),4):
    imout=Image.new("RGB",(w*2,(h+32)*2),(238,238,238));d=ImageDraw.Draw(imout)
    for j,path in enumerate(pages[start:start+4]):
        im=Image.open(path).convert("RGB");im.thumbnail((w,h))
        x=(j%2)*w+(w-im.width)//2;y=(j//2)*(h+32)+24
        imout.paste(im,(x,y));d.text(((j%2)*w+8,(j//2)*(h+32)+5),f"Page {start+j+1}",fill=(0,0,0))
    imout.save(sheets/f"sheet-{start//4+1:02d}.png")
print(len(pages),len(list(sheets.glob("sheet-*.png"))))
