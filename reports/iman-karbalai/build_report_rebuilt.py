# -*- coding: utf-8 -*-
"""Build Iman's independent Persian BSc report from evidence-based Markdown."""
from pathlib import Path
import re,json,math,sys
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image,ImageDraw,ImageFont,features
ROOT=Path(__file__).resolve().parent
D=Document(); TABLES=json.loads((ROOT/'tables.json').read_text('utf-8'))
DEFS=json.loads((ROOT/'diagrams.json').read_text('utf-8'))
TEXT=(ROOT/'report-text-final.md').read_text('utf-8')
# Keep Markdown headings and directives in their own Word paragraphs.
TEXT=re.sub(r'^(#{1,3} [^\n]+|@(?:figure|table|screenshot) [^\n]+)\n(?=\S)',r'\1\n\n',TEXT,flags=re.M)
def fa_num(value): return str(value).translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'))
FIG_KEYS=[]; TAB_KEYS=[]
for _line in TEXT.splitlines():
 if _line.startswith('@figure '): FIG_KEYS.append(_line[8:].split(' | ',1)[0])
 elif _line.startswith('@screenshot '): FIG_KEYS.append(_line[12:].split(' | ',1)[0])
 elif _line.startswith('@table '): TAB_KEYS.append(_line[7:].split(' | ',1)[0])
FIG_REFS={key:'شکل '+fa_num(i) for i,key in enumerate(FIG_KEYS,1)}
TAB_REFS={key:'جدول '+fa_num(i) for i,key in enumerate(TAB_KEYS,1)}
def resolve_refs(text):
 for key,label in FIG_REFS.items(): text=text.replace('{{fig:'+key+'}}',label)
 for key,label in TAB_REFS.items(): text=text.replace('{{tab:'+key+'}}',label)
 return text
FONT='B Nazanin'; LATIN='Times New Roman'; BLACK=RGBColor(0,0,0)

def elem(parent,tag,attrs=None,text=None):
 e=parent.find(qn(tag))
 if e is None:
  e=OxmlElement(tag);parent.append(e)
 for k,v in (attrs or {}).items():e.set(qn(k),str(v))
 if text is not None:e.text=text
 return e

def direction(p,rtl=True):
 pp=p._p.get_or_add_pPr(); elem(pp,'w:bidi',{'w:val':1});elem(pp,'w:jc',{'w:val':'start'})

def run(p,text,size=14,bold=False,rtl=True):
 r=p.add_run(text);r.font.name=LATIN;r.font.size=Pt(size);r.font.bold=bold;r.font.color.rgb=BLACK
 pr=r._r.get_or_add_rPr()
 f=pr.find(qn('w:rFonts'))
 if f is None:f=elem(pr,'w:rFonts')
 for k,v in {'ascii':LATIN,'hAnsi':LATIN,'cs':FONT if rtl else LATIN,'eastAsia':FONT if rtl else LATIN}.items():f.set(qn('w:'+k),v)
 elem(pr,'w:szCs',{'w:val':size*2});elem(pr,'w:rtl',{'w:val':1})
 if bold:elem(pr,'w:bCs',{'w:val':1})
 elem(pr,'w:lang',{'w:val':'fa-IR' if rtl else 'en-US','w:bidi':'fa-IR'})
 return r

PAT=re.compile(r'[A-Za-z0-9_/][A-Za-z0-9_./:#?=&%+\[\]{}()\-]*(?: +[A-Za-z0-9_/][A-Za-z0-9_./:#?=&%+\[\]{}()\-]*)*')
def mixed(p,text,size=14,bold=False):
 pos=0
 for m in PAT.finditer(text):
  if m.start()>pos:run(p,text[pos:m.start()],size,bold,True)
  run(p,m.group(),size,bold,False);pos=m.end()
 if pos<len(text):run(p,text[pos:],size,bold,True)
 return p

def para(text='',style=None,align='justify',size=14,bold=False,rtl=True,before=0,after=6):
 p=D.add_paragraph(style=style);direction(p,rtl)
 if align=='center':
  tabs=elem(p._p.get_or_add_pPr(),'w:tabs');elem(tabs,'w:tab',{'w:val':'center','w:pos':'4680'})
  p.add_run().add_tab()
 pf=p.paragraph_format;pf.line_spacing=1;pf.space_before=Pt(before);pf.space_after=Pt(after);pf.widow_control=True
 if rtl:mixed(p,resolve_refs(text),size,bold)
 else:run(p,text,size,bold,False)
 return p

def style_setup():
 from docx.enum.style import WD_STYLE_TYPE
 for name,size,bold in [('Normal',14,False),('Title',20,True),('Heading 1',20,True),('Heading 2',18,True),('Heading 3',16,True),('Caption',12,False),('Figure Caption',12,False),('Table Caption',12,False),('Code',10,False),('Evidence',11,False)]:
  s=D.styles[name] if name in D.styles else D.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
  s.font.name=LATIN;s.font.size=Pt(size);s.font.bold=bold;s.font.color.rgb=BLACK
  rp=s.element.get_or_add_rPr();elem(rp,'w:rFonts',{'w:ascii':LATIN,'w:hAnsi':LATIN,'w:cs':FONT});elem(rp,'w:szCs',{'w:val':size*2});elem(rp,'w:lang',{'w:val':'fa-IR','w:bidi':'fa-IR'})
  if bold:elem(rp,'w:bCs',{'w:val':1})
  s.paragraph_format.line_spacing=1;s.paragraph_format.space_after=Pt(6)
  if name.startswith('Heading'):s.paragraph_format.keep_with_next=True;s.paragraph_format.space_before=Pt(10)
  elem(s.element.get_or_add_pPr(),'w:bidi',{'w:val':1});elem(s.element.get_or_add_pPr(),'w:jc',{'w:val':'start'})
 for i in range(1,4):
  n='TOC '+str(i);s=D.styles[n] if n in D.styles else D.styles.add_style(n,WD_STYLE_TYPE.PARAGRAPH)
  s.font.name=LATIN;s.font.size=Pt(14);elem(s.element.get_or_add_rPr(),'w:rFonts',{'w:ascii':LATIN,'w:hAnsi':LATIN,'w:cs':FONT});elem(s.element.get_or_add_rPr(),'w:szCs',{'w:val':28});elem(s.element.get_or_add_pPr(),'w:bidi',{'w:val':1})
style_setup()
# The built-in Word Title style carries a blue bottom rule; university covers do not.
_title_pr=D.styles['Title'].element.get_or_add_pPr()
_title_border=_title_pr.find(qn('w:pBdr'))
if _title_border is not None:_title_pr.remove(_title_border)
settings=D.settings.element
for tag in ['w:mirrorMargins','w:evenAndOddHeaders']:elem(settings,tag)
elem(settings,'w:updateFields',{'w:val':1});elem(settings,'w:themeFontLang',{'w:val':'en-US','w:bidi':'fa-IR'})

def margins(s):
 s.page_width=Cm(21);s.page_height=Cm(29.7)
 s.top_margin=Cm(3.5);s.bottom_margin=Cm(2);s.left_margin=Cm(2);s.right_margin=Cm(2.5)
 s.header_distance=Cm(2.5);s.footer_distance=Cm(1)
 elem(s._sectPr,'w:rtlGutter')

def field(p,instruction,cache=''):
 a=run(p,'',12);elem(a._r,'w:fldChar',{'w:fldCharType':'begin','w:dirty':1})
 b=run(p,'',12,rtl=False);elem(b._r,'w:instrText',{'xml:space':'preserve'},instruction)
 c=run(p,'',12);elem(c._r,'w:fldChar',{'w:fldCharType':'separate'})
 if cache:mixed(p,cache,14)
 z=run(p,'',12);elem(z._r,'w:fldChar',{'w:fldCharType':'end'})

def blank_headers(s):
 for h in [s.header,s.even_page_header,s.first_page_header,s.footer,s.even_page_footer,s.first_page_footer]:
  h.is_linked_to_previous=False
  for p in h.paragraphs:p.clear()

def furniture(s,title,start=None):
 margins(s);s.different_first_page_header_footer=True;blank_headers(s)
 for h,label,align in [(s.header,title,WD_ALIGN_PARAGRAPH.RIGHT),(s.even_page_header,'گزارش پروژه کارشناسی',WD_ALIGN_PARAGRAPH.LEFT)]:
  p=h.paragraphs[0];direction(p);p.alignment=align;pf=p.paragraph_format;pf.line_spacing=1;pf.space_after=Pt(0)
  mixed(p,label,11);p.paragraph_format.tab_stops.add_tab_stop(Cm(15.5),WD_ALIGN_PARAGRAPH.RIGHT)
  run(p,'\t',11);field(p,' PAGE ')
 for f in [s.first_page_footer]:
  p=f.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER;field(p,' PAGE ')
 pg=s._sectPr.find(qn('w:pgNumType'))
 if pg is not None:s._sectPr.remove(pg)
 if start is not None:elem(s._sectPr,'w:pgNumType',{'w:start':start})

def bookmark(p,name,bid):
 st=OxmlElement('w:bookmarkStart');st.set(qn('w:id'),str(bid));st.set(qn('w:name'),name);p._p.insert(0,st)
 elem(p._p,'w:bookmarkEnd',{'w:id':bid})

def heading(text,level=2):
 return para(text,style='Heading '+str(level),align='right',size={1:20,2:18,3:16}[level],bold=True,before=10,after=8)

def pb():
 p=para('',align='right',after=0);p.paragraph_format.line_spacing=1;p.add_run().add_break(WD_BREAK.PAGE)

def cap(text,kind):
 p=para(text,style=kind+' Caption',align='center',size=12,after=8);return p

s=D.sections[0];margins(s);blank_headers(s)
logo=ROOT/'assets/university-logo.png'
if logo.exists():
 p=para('',align='center',after=5);p.add_run().add_picture(str(logo),width=Cm(3.0))
for text in ['دانشگاه تهران','دانشکدگان فارابی','دانشکده مهندسی','گروه مهندسی کامپیوتر']:para(text,align='center',size=16,bold=True,after=4)
para('طراحی و پیاده‌سازی دستیار هوشمند بالینی مبتنی بر تلفیق پرونده بیمار و دانش پزشکی معتبر',style='Title',align='center',size=20,bold=True,before=60,after=7)
para('Clinical AI Copilot',align='center',size=16,bold=True,rtl=False,after=28)
para('نگارش',align='center',after=4);para('ایمان کربلائی',align='center',size=18,bold=True,after=24)
para('استاد راهنما',align='center',after=4);para('دکتر کاظم فولادی قلعه',align='center',size=18,bold=True,after=35)
para('گزارش پروژه برای دریافت درجه کارشناسی در رشته مهندسی کامپیوتر',align='center',size=16,bold=True,after=20)
para('سال تحصیلی ۱۴۰۵–۱۴۰۶',align='center');para('ماه و سال ارائه: مهر ۱۴۰۵',align='center',size=12)
pb();pb()  # back of cover; Bismillah begins on its own page
b=para('',align='center',after=0);bookmark(b,'BismillahReserved',1000)
bismillah=ROOT/'assets/bismillah.png'
if bismillah.exists():
 b.add_run().add_picture(str(bismillah),width=Cm(13.0))
pb();pb()  # Bismillah reverse; administrative page
para('مشخصات جلسه داوری',style='Title',align='center',size=20,bold=True,after=25)
for text in ['نام دانشجو: ایمان کربلائی','شماره دانشجویی: ۲۲۰۷۰۱۰۸۷','عنوان پروژه: طراحی و پیاده‌سازی دستیار هوشمند بالینی (Clinical AI Copilot) مبتنی بر تلفیق پرونده بیمار و دانش پزشکی معتبر','استاد راهنما: دکتر کاظم فولادی قلعه','تاریخ جلسه:','اعضای هیئت داوری:','نتیجه و نمره:','محل امضاها: ..........................................................']:para(text,align='right',after=14)
pb();pb()
para('چکیده',style='Title',size=20,bold=True,align='center',after=20)
para('این پروژه یک دستیار بالینی تحت وب است که اطلاعات پرونده بیمار، اسناد، یادداشت صوتی و گفت‌وگوی مبتنی بر مدل زبانی را در یک محیط فارسی کنار هم قرار می‌دهد. گزارش بر بخشی تمرکز دارد که در تقسیم کار پروژه به ایمان کربلائی سپرده شده است: معماری فرانت‌اند و طراحی گردش کار پزشک. رابط با Next.js، React و TypeScript ساخته شده و داده‌های هر بخش را از API دریافت می‌کند. جداسازی اطلاعات ثبت‌شده پرونده از پاسخ مدل، نمایش وضعیت عملیات و امکان بازبینی متن پیش از ذخیره، از تصمیم‌های اصلی این پیاده‌سازی‌اند.')
para('در بررسی نسخه فعلی، مسیر ورود، مدیریت بیمار، خلاصه پرونده، تایم‌لاین، اسناد، یادداشت صوتی، گفت‌وگوی بالینی و ایمنی دارو دنبال شد. بعضی قابلیت‌های سرور هنوز در رابط کامل نشده‌اند و مسیر آزمایشی Agent نیز جدا از گفت‌وگوی اصلی باقی مانده است. ساخت production و بررسی TypeScript موفق بود، اما ESLint هفت خطا و دو هشدار گزارش کرد. آزمون مرورگری با داده کاملاً ساختگی انجام شد و شامل ارزیابی بالینی، OCR واقعی، رونویسی صوت یا سنجش کیفیت پاسخ مدل نبود.')
para('کلیدواژه‌ها: رابط کاربری فارسی، Next.js، پرونده بیمار، مستندسازی صوتی، گفت‌وگوی بالینی، شواهد داخلی، کاربردپذیری، تصمیم‌یار بالینی.',size=14,align='right')
pb();pb()
para('فهرست مطالب',style='Title',align='center',size=20,bold=True,after=14)
cached_titles='\n'.join(line[2:].replace(' — ',' ') for line in TEXT.splitlines() if line.startswith('# '))
p=para('',after=0);field(p,' TOC \\o "1-2" \\h \\z \\u ',cached_titles)
para('فهرست شکل‌ها',style='Title',align='center',size=20,bold=True,before=20)
p=para('',after=0);field(p,' TOC \\t "Figure Caption,1" \\h \\z ')
para('فهرست جدول‌ها',style='Title',align='center',size=20,bold=True,before=20)
p=para('',after=0);field(p,' TOC \\t "Table Caption,1" \\h \\z ')

# True RTL text is shaped with Raqm in task-local diagrams.
assets=ROOT/'assets';assets.mkdir(exist_ok=True)
FAFILE=Path('C:/Windows/Fonts/BNazanin.ttf')
BOLD=Path('C:/Windows/Fonts/BNazannO.ttf')
ENG=Path('C:/Windows/Fonts/arial.ttf')
raqm=features.check_feature('raqm')

def gdi_labels(image,labels):
 import ctypes as C
 from ctypes import wintypes as W
 class BIH(C.Structure):
  _fields_=[('biSize',W.DWORD),('biWidth',W.LONG),('biHeight',W.LONG),('biPlanes',W.WORD),('biBitCount',W.WORD),('biCompression',W.DWORD),('biSizeImage',W.DWORD),('biXPelsPerMeter',W.LONG),('biYPelsPerMeter',W.LONG),('biClrUsed',W.DWORD),('biClrImportant',W.DWORD)]
 class BMI(C.Structure):_fields_=[('h',BIH),('colors',W.DWORD*3)]
 g=C.WinDLL('gdi32');u=C.WinDLL('user32')
 g.CreateCompatibleDC.argtypes=[W.HDC];g.CreateCompatibleDC.restype=W.HDC
 g.CreateDIBSection.argtypes=[W.HDC,C.POINTER(BMI),W.UINT,C.POINTER(C.c_void_p),W.HANDLE,W.DWORD];g.CreateDIBSection.restype=W.HBITMAP
 g.SelectObject.argtypes=[W.HDC,W.HGDIOBJ];g.SelectObject.restype=W.HGDIOBJ
 g.CreateFontW.argtypes=[C.c_int]*5+[W.DWORD]*8+[W.LPCWSTR];g.CreateFontW.restype=W.HFONT
 g.SetBkMode.argtypes=[W.HDC,C.c_int];g.SetTextColor.argtypes=[W.HDC,W.DWORD]
 u.DrawTextW.argtypes=[W.HDC,W.LPCWSTR,C.c_int,C.POINTER(W.RECT),W.UINT];u.DrawTextW.restype=C.c_int
 g.DeleteObject.argtypes=[W.HGDIOBJ];g.DeleteDC.argtypes=[W.HDC]
 w,h=image.size;dc=g.CreateCompatibleDC(None);bmi=BMI();bmi.h=BIH(C.sizeof(BIH),w,-h,1,32,0,w*h*4,0,0,0,0)
 ptr=C.c_void_p();bitmap=g.CreateDIBSection(dc,C.byref(bmi),0,C.byref(ptr),None,0);old=g.SelectObject(dc,bitmap)
 C.memmove(ptr,image.tobytes('raw','BGRX'),w*h*4);g.SetBkMode(dc,1);g.SetTextColor(dc,0x232614)
 for text,(x,y),size,family in labels:
  font=g.CreateFontW(-size,0,0,0,400,0,0,0,1,0,0,5,0,family);previous=g.SelectObject(dc,font)
  rect=W.RECT(int(x-450),int(y-70),int(x+450),int(y+70));flags=0x1|0x4|0x20|0x800|0x20000
  u.DrawTextW(dc,text,len(text),C.byref(rect),flags)
  g.SelectObject(dc,previous);g.DeleteObject(font)
 result=Image.frombytes('RGB',(w,h),C.string_at(ptr,w*h*4),'raw','BGRX')
 g.SelectObject(dc,old);g.DeleteObject(bitmap);g.DeleteDC(dc);return result

def draw_diagram(name):
 spec=DEFS[name];im=Image.new('RGB',(2400,1560),'white');dr=ImageDraw.Draw(im)
 fa=ImageFont.truetype(str(FAFILE),65);en=ImageFont.truetype(str(ENG),45);labels=[]
 def label(text,xy,font=fa):
  labels.append((text,xy,font.size,'B Nazanin' if re.search('[\u0600-\u06ff]',text) else 'Arial'))
 label(spec['title'],(1200,90))
 boxes=[]
 for i in range(6):
  x=1320 if i%2==0 else 160;y=230+(i//2)*450;boxes.append((x,y,x+920,y+290))
 for a,b in spec['edges']:
  A=boxes[a];B=boxes[b];ax=(A[0]+A[2])/2;ay=(A[1]+A[3])/2;bx=(B[0]+B[2])/2;by=(B[1]+B[3])/2
  if abs(ay-by)<10:
   p=(A[0] if bx<ax else A[2],ay);q=(B[2] if bx<ax else B[0],by)
  else:p=(ax,A[3]);q=(bx,B[1])
  if abs(a//2-b//2)>=2:
   rail=2320 if a%2==0 else 80
   start=(A[2] if a%2==0 else A[0],ay);q=(bx,B[3]);path=[start,(rail,ay),(rail,1500),(bx,1500),q]
   dr.line(path,fill='#526762',width=6);p=path[-2]
  else:dr.line([p,q],fill='#526762',width=6)
  ang=math.atan2(q[1]-p[1],q[0]-p[0]);L=25
  dr.polygon([q,(q[0]-L*math.cos(ang-.45),q[1]-L*math.sin(ang-.45)),(q[0]-L*math.cos(ang+.45),q[1]-L*math.sin(ang+.45))],fill='#526762')
 for i,(title,sub) in enumerate(spec['nodes']):
  x1,y1,x2,y2=boxes[i];dr.rounded_rectangle((x1,y1,x2,y2),radius=14,fill='#f5f8f7',outline='#8ba09a',width=4)
  label(title,((x1+x2)/2,y1+95));label(sub,((x1+x2)/2,y1+190),fa if re.search('[\u0600-\u06ff]',sub) else en)
 target=assets/(name+'.png');gdi_labels(im,labels).save(target);return target
for name in DEFS:draw_diagram(name)

def figure(name,title):
 title=re.sub(r'^\{\{fig:[^}]+\}\}\s*','',title)
 p=para('',align='center',after=3);p.paragraph_format.keep_with_next=True
 r=p.add_run();r.add_picture(str(assets/(name+'.png')),width=Cm(16.5));r._r.xpath('.//wp:docPr')[0].set('descr',title)
 cap(FIG_REFS[name]+' ـ '+title,'Figure')

def screenshot(name,title):
 path=ROOT/'screenshots'/name
 with Image.open(path) as im: ratio=im.width/im.height
 width=min(16.5,14.2*ratio)
 p=para('',align='center',after=3);p.paragraph_format.keep_with_next=True
 r=p.add_run();r.add_picture(str(path),width=Cm(width));r._r.xpath('.//wp:docPr')[0].set('descr',title)
 cap(FIG_REFS[name]+' ـ '+title,'Figure')

def table(name,title):
 title=re.sub(r'^\{\{tab:[^}]+\}\}\s*','',title)
 p=cap(TAB_REFS[name]+' ـ '+title,'Table');p.paragraph_format.keep_with_next=True
 rows=TABLES[name];t=D.add_table(rows=len(rows),cols=len(rows[0]));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
 widths=[5.0,5.5,6.0]
 pr=t._tbl.tblPr;elem(pr,'w:bidiVisual');b=elem(pr,'w:tblBorders')
 for edge in ['top','left','bottom','right','insideH','insideV']:elem(b,'w:'+edge,{'w:val':'single','w:sz':4,'w:color':'D9D9D9'})
 mar=elem(pr,'w:tblCellMar')
 for side in ['top','bottom','left','right']:elem(mar,'w:'+side,{'w:w':90,'w:type':'dxa'})
 for j,w in enumerate(widths):t.columns[j].width=Cm(w)
 for i,row in enumerate(rows):
  tr=t.rows[i]._tr.get_or_add_trPr();elem(tr,'w:cantSplit')
  if i==0:elem(tr,'w:tblHeader')
  for j,text in enumerate(row):
   c=t.cell(i,j);c.width=Cm(widths[j]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;c.text=''
   p=c.paragraphs[0];direction(p);p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=False
   mixed(p,text,12,i==0)
   if i==0:elem(c._tc.get_or_add_tcPr(),'w:shd',{'w:fill':'E7ECEB'})
 para('',after=2)

first=True
for block in re.split(r'\n\s*\n',TEXT):
 block=block.strip()
 if not block:continue
 if block.startswith('# '):
  sec=D.add_section(WD_SECTION_START.ODD_PAGE);title=fa_num(block[2:].replace(' — ',' '))
  furniture(sec,title,1 if first else None);p=heading(title,1)
  if first:bookmark(p,'MainBodyStart',2001);first=False
 elif block.startswith('## '):heading(fa_num(block[3:]),2)
 elif block.startswith('@figure '):
  name,title=block[8:].split(' | ',1);figure(name,title)
 elif block.startswith('@table '):
  name,title=block[7:].split(' | ',1);table(name,title)
 elif block.startswith('@screenshot '):
  name,title=block[12:].split(' | ',1);screenshot(name,title)
 elif block.startswith('مبنای '):para(block,style='Evidence',size=11,align='right')
 else:para(block)
last=para('',after=0);bookmark(last,'MainBodyEnd',2002)

"""Legacy references, long appendices, and the English cover were intentionally removed.
sec=D.add_section(WD_SECTION_START.ODD_PAGE);furniture(sec,'منابع و مراجع')
heading('منابع و مراجع',1)
para('منابع فنی بیرونی برای مبانی به کار رفته‌اند. شواهد قابلیت پروژه، فایل‌های مخزن و اسناد رسمی محلی هستند. تاریخ دسترسی به منابع وب: ۱۵ اکتبر ۲۰۲۶.',align='right')
refs=json.loads((ROOT/'references.json').read_text('utf-8'))
for i,(author,title,url) in enumerate(refs,1):
 para('['+str(i)+'] '+author+'. '+title+'. Accessed 2026-10-15.',rtl=False,align='left',size=12,after=3)
 para(url,rtl=False,align='left',size=11,after=10)
heading('منابع پروژه',2)
for x in ['پروپوزال پروژه پایانی دوره کارشناسی، بخش تقسیم وظایف و معیارهای ارزیابی؛ سال تحصیلی۱۴۰۴–۱۴۰۵.','راهنمای ساختار و قالب گزارش پروژه کارشناسی دانشگاه تهران؛ BSc-project-report-format.pdf.','الگوی جلد فارسی؛ BSc-project-report-cover-fa-1401.pdf؛ تاریخ نمونه، تاریخ ارائه این گزارش محسوب نشده است.','مخزن Clinical AI Copilot، نسخه56ed451 به همراه working tree موجود در۱۵اکتبر۲۰۲۶؛ نشانی فایل‌ها در متن و پیوست.']:para(x)
sec=D.add_section(WD_SECTION_START.ODD_PAGE);furniture(sec,'پیوست‌ها');heading('پیوست‌ها',1)
heading('پیوست الف نمونه درخواست‌های توضیحی',2)
para('نمونه‌های زیر مصنوعی و صرفاً برای توضیح شکل قرارداد هستند. پاسخ پزشکی یا نتیجه فراخوانی واقعی مدل نیستند و هیچ داده بیمار واقعی در آن‌ها استفاده نشده است.')
samples=[('ایجاد بیمار',{'first_name':'بیمار','last_name':'فرضی','gender':'unknown','national_code':None}),('ثبت یادداشت پس از بازبینی رونوشت',{'title':'یادداشت نمونه','content':'متن فرضی بازبینی‌شده برای نمایش قرارداد'}),('پیام گفتگو',{'content':'فهرست داده‌های ثبت‌شده را مرور کن','medication_safety':False}),('کاندید تحلیل دارو',{'medications':[{'name':'نام داروی فرضی','dose':None}]})]
for title,data in samples:
 heading(title,3);p=para(json.dumps(data,ensure_ascii=False,indent=2),style='Code',align='left',rtl=False,size=10)
 for r in p.runs:
  r.font.name='Consolas';r._r.get_or_add_rPr().find(qn('w:rFonts')).set(qn('w:cs'),FONT)
heading('پیوست ب گزیده‌های کوتاه پیاده‌سازی',2)
codes=[('جهت عمومی صفحه','<html lang="fa" dir="rtl">','از layout.tsx؛ جهت متن در سطح سند تعیین می‌شود و قالب اجزای تعاملی با DirectionProvider هماهنگ است.'),('ساخت بدنه فایل','const body = new FormData();\nbody.append("file", form.file);','از api.ts؛ boundary در درخواست مرورگر ساخته می‌شود و Content-Type دستی برای FormData تنظیم نمی‌شود.'),('پیام از رابط به سرور','content: trimmed,\nmedication_safety: safetyMode,\nprovider: selectedProvider ?? undefined,\nmodel: selectedModel ?? undefined,','گزیده payload در clinical-chat.tsx؛ تنها شناسه تنظیم می‌رود و کلید سرویس AI در مرورگر داده نمی‌شود.'),('قطع دارو بدون حذف','status: "stopped",\nend_date: todayIsoDate(),','گزیده payload در medication-actions.tsx؛ تغییر وضعیت با حذف رکورد فرق دارد و تاریخ از تابع فعلی UTC می‌آید.')]
for title,code,expl in codes:
 heading(title,3);p=para(code,style='Code',rtl=False,align='left',size=10)
 for r in p.runs:
  r.font.name='Consolas';rf=r._r.get_or_add_rPr().find(qn('w:rFonts'))
  for key in ['ascii','hAnsi','cs']:rf.set(qn('w:'+key),'Consolas')
 para(expl)
heading('پیوست پ نمایه شواهد پیاده‌سازی',2)
para('نشانی‌ها نسبت به ریشه مخزن نوشته شده‌اند. این نمایه برای بازبینی فنی است؛ ماتریس تفصیلی و نتیجه بررسی‌ها در فایل‌های همراه نگه‌داری می‌شوند.')
for path in ['frontend/src/app/layout.tsx','frontend/src/app/globals.css','frontend/src/app/patients/page.tsx','frontend/src/app/patients/[id]/page.tsx','frontend/src/app/login/page.tsx','frontend/src/lib/api.ts','frontend/src/lib/auth.ts','frontend/src/lib/types.ts','frontend/src/lib/format.ts','frontend/src/components/patients/document-actions.tsx','frontend/src/components/patients/voice-note-actions.tsx','frontend/src/components/patients/clinical-chat.tsx','frontend/src/components/patients/medication-actions.tsx','frontend/src/components/patients/copilot/evidence-list.tsx','backend/app/api/v1/dependencies.py','backend/app/api/v1/routes/conversations.py','backend/app/services/evidence.py','deploy/docker-compose.prod.yml','deploy/nginx/nginx.conf']:
 para(path,rtl=False,align='left',size=11,after=3)
heading('پیوست ت واژه‌نامه',2)
for en,fa in [('Frontend','لایه تعامل و ارائه در مرورگر و صفحات وب'),('Patient Context','زمینه منتخب بیمار برای نمایش یا درخواست مدل'),('Provenance','قابلیت پیگیری منشأ داده در رکورد یا فایل'),('Transcript','رونوشت متن حاصل از صوت'),('Diarization','تفکیک گویندگان صوت، بدون اثبات نقش بالینی'),('SSR','تولید صفحه در سمت سرور'),('RSC','مؤلفه سرور React در معماری Next.js'),('MVP','نمونه کمینه با دامنه محدود و قابل بررسی'),('SUS','مقیاس کاربردپذیری پیشنهادی پروپوزال؛ در این بررسی اجرا نشده')]:para(en+' — '+fa,align='right')
sec=D.add_section(WD_SECTION_START.ODD_PAGE);margins(sec);blank_headers(sec)
for x in ['University of Tehran','College of Farabi','Faculty of Engineering','Department of Computer Engineering']:para(x,align='center',rtl=False,size=16,bold=True,after=4)
para('Design and Implementation of an AI Clinical Copilot Based on Integration of Patient Context and Validated Medical Knowledge',style='Title',align='center',rtl=False,size=20,bold=True,before=70,after=45)
para('Bachelor’s Project Report',align='center',rtl=False,size=16,bold=True,after=20)
para('Iman Karbalai',align='center',rtl=False,size=18,bold=True,after=25)
para('Supervisor',align='center',rtl=False,size=14,after=5);para('دکتر کاظم فولادی قلعه',align='center',size=16,bold=True,after=40)
para('Submission month and year: [To be completed]',align='center',rtl=False,size=12)
"""
D.core_properties.title='گزارش پروژه کارشناسی ایمان کربلائی';D.core_properties.subject='معماری فرانت‌اند و گردش کار بالینی Clinical AI Copilot';D.core_properties.author='ایمان کربلائی';D.core_properties.keywords='Frontend, Clinical AI Copilot, Persian RTL, BSc'
file=ROOT/'گزارش_پروژه_کارشناسی_ایمان_کربلائی.docx';D.save(file)
# Remove template statistics; they are not measured pagination or word counts.
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree
with ZipFile(file) as z:parts={x.filename:z.read(x.filename) for x in z.infolist()}
app=etree.fromstring(parts['docProps/app.xml'])
for e in list(app):
 if etree.QName(e).localname in ['Pages','Words','Characters','CharactersWithSpaces','Lines','Paragraphs']:app.remove(e)
parts['docProps/app.xml']=etree.tostring(app,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(file,'w',ZIP_DEFLATED) as z:
 for name,data in parts.items():z.writestr(name,data)

print(json.dumps({'file':str(file),'main_body_words':len(TEXT.split()),'sections':len(D.sections),'tables':len(D.tables),'figures':len(D.inline_shapes),'raqm':raqm},ensure_ascii=True))
