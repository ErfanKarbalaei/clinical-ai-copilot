"""Make native-resolution two-page boards, without changing report images."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent
q=OUT/'review-qa-pages'
pages=sorted(q.glob('page-*.png'))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for start in range(0,len(pages),2):
    selected=pages[start:start+2];ims=[Image.open(p).convert('RGB') for p in selected]
    w=sum(im.width for im in ims)+12;h=max(im.height for im in ims)+30
    board=Image.new('RGB',(w,h),'#dddddd');dr=ImageDraw.Draw(board);x=0
    for im,p in zip(ims,selected):
        board.paste(im,(x,30));dr.text((x+8,3),p.stem,font=font,fill='black');x+=im.width+12
    board.save(q/f'review-pair-{start+1:03d}-{start+len(ims):03d}.png')
print('Native-size QA boards:',(len(pages)+1)//2)
