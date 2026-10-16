# -*- coding: utf-8 -*-
from pathlib import Path
import json,sys
import win32com.client,pythoncom
import pymupdf
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
DOC=R/'گزارش_پروژه_کارشناسی_ایمان_کربلائی.docx'
PDF=DOC.with_suffix('.pdf')
pythoncom.CoInitialize()
app=win32com.client.DispatchEx('Word.Application');app.Visible=False;app.DisplayAlerts=0
word=None
try:
 word=app.Documents.Open(str(DOC),ConfirmConversions=False,ReadOnly=False,AddToRecentFiles=False)
 word.Fields.Update()
 for toc in word.TablesOfContents:
  toc.Update()
  toc.Range.ParagraphFormat.ReadingOrder=0
  toc.Range.ParagraphFormat.Alignment=2
  toc.Range.Font.Name='B Nazanin';toc.Range.Font.NameBi='B Nazanin'
  toc.Range.Font.Size=14;toc.Range.Font.SizeBi=14
  toc.Range.ParagraphFormat.LineSpacingRule=0
  toc.Range.ParagraphFormat.SpaceAfter=3
 for sec in word.Sections:
  p=sec.Range.Paragraphs.Last
  if not p.Range.Text.strip('\r\x0c\x07 \t'):
   p.Range.Font.Size=1;p.Range.Font.SizeBi=1
   p.Format.SpaceBefore=0;p.Format.SpaceAfter=0
   p.Format.LineSpacingRule=4;p.Format.LineSpacing=1
 word.Repaginate()
 for toc in word.TablesOfContents: toc.UpdatePageNumbers()
 start=word.Bookmarks('MainBodyStart').Range.Information(3)
 end=word.Bookmarks('MainBodyEnd').Range.Information(3)
 pages=word.ComputeStatistics(2)
 word.Save()
 word.ExportAsFixedFormat(str(PDF),17,OpenAfterExport=False,OptimizeFor=0,CreateBookmarks=1)
 meta={'word_version':str(app.Version),'word_pages':pages,'main_start':start,'main_end':end,'toc_count':word.TablesOfContents.Count}
finally:
 if word is not None:word.Close(False)
 app.Quit();pythoncom.CoUninitialize()
pdf=pymupdf.open(str(PDF))
meta['pdf_pages']=len(pdf)
summary=[]
renderdir=R/'rendered';renderdir.mkdir(exist_ok=True)
for i,p in enumerate(pdf,1):
 words=p.get_text('words')
 # Ignore the repeated top header and bottom page number when finding blank bodies.
 body=[w for w in words if 95<=w[1]<=790]
 summary.append({'page':i,'words':len(words),'body_words':len(body),'images':len(p.get_images()),'head':p.get_text()[:100]})
 p.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3),alpha=False).save(str(renderdir/f'page-{i:03d}.png'))
meta['body_nonblank_pages']=sum(1 for x in summary if start<=x['page']<=end and x['body_words']>=20)
meta['body_blank_or_tiny_pages']=[x['page'] for x in summary if start<=x['page']<=end and x['body_words']<20]
meta['page_summary']=summary
(R/'pagination-rebuilt.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
for start_idx in range(0,len(pdf),12):
 sheet=Image.new('RGB',(1440,4*530),'#E9EEEE');draw=ImageDraw.Draw(sheet)
 for j in range(start_idx,min(start_idx+12,len(pdf))):
  im=Image.open(renderdir/f'page-{j+1:03d}.png');im.thumbnail((460,490))
  x=(j-start_idx)%3*480+(480-im.width)//2;y=(j-start_idx)//3*530+30
  sheet.paste(im,(x,y));draw.text((x,y-25),f'Page {j+1} / {summary[j]["body_words"]} body words',font=font,fill='black')
 sheet.save(renderdir/f'contact-{start_idx//12+1:02d}.jpg',quality=87)
print(json.dumps({k:v for k,v in meta.items() if k!='page_summary'},ensure_ascii=False))
