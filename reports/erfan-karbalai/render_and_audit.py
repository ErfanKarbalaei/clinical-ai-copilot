"""Render DOCX with installed Microsoft Word, then count/rasterize its PDF."""
from pathlib import Path
import sys,json,time,re,zipfile
from lxml import etree
import pymupdf
OUT=Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding='utf-8')
DOCX=OUT/'گزارش_پروژه_کارشناسی_عرفان_کربالئی.docx'
PDF=DOCX.with_suffix('.pdf')
if '--images' not in sys.argv:
    import win32com.client,pythoncom
    pythoncom.CoInitialize()
    app=win32com.client.DispatchEx('Word.Application')
    app.Visible=False;app.DisplayAlerts=0
    doc=None
    try:
        doc=app.Documents.Open(str(DOCX),ConfirmConversions=False,ReadOnly=False,AddToRecentFiles=False)
        print('Opened Word',app.Version,flush=True)
        doc.Fields.Update()
        for toc in doc.TablesOfContents:
            toc.Update()
            toc.Range.ParagraphFormat.ReadingOrder=0
            toc.Range.ParagraphFormat.Alignment=2
            toc.Range.Font.Name='B Nazanin';toc.Range.Font.NameBi='B Nazanin'
            toc.Range.Font.Size=14;toc.Range.Font.SizeBi=14
            toc.Range.ParagraphFormat.LineSpacingRule=0
            toc.Range.ParagraphFormat.SpaceAfter=3
        # Word's TOC update can reset the empty section-break paragraph to
        # 14 pt, causing a header-only spill page. Keep only empty breaks tiny.
        for sec in doc.Sections:
            endp=sec.Range.Paragraphs.Last
            if not endp.Range.Text.strip('\r\x0c\x07 \t'):
                endp.Range.Font.Size=1;endp.Range.Font.SizeBi=1
                endp.Format.SpaceBefore=0;endp.Format.SpaceAfter=0
                endp.Format.LineSpacingRule=4;endp.Format.LineSpacing=1
        doc.Repaginate()
        for toc in doc.TablesOfContents:toc.UpdatePageNumbers()
        records=json.loads((OUT/'sections.json').read_text(encoding='utf-8'))
        for item in records:
            rng=doc.Bookmarks(item['bookmark']).Range
            item['physical_page']=rng.Information(3)
            item['display_page']=rng.Information(1)
        pages=doc.ComputeStatistics(2)
        doc.Save()
        doc.ExportAsFixedFormat(str(PDF),17,OpenAfterExport=False,OptimizeFor=0,CreateBookmarks=1)
        meta={'word_version':str(app.Version),'word_pages':pages,'sections':records}
        (OUT/'render-metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Exported PDF:',pages,'pages',flush=True)
    finally:
        if doc is not None:doc.Close(False)
        app.Quit();pythoncom.CoUninitialize()

pdf=pymupdf.open(PDF)
meta=json.loads((OUT/'render-metadata.json').read_text(encoding='utf-8'))
sections=meta['sections']
main_start=next(x['physical_page'] for x in sections if x['kind']=='main')
refs_start=next(x['physical_page'] for x in sections if x['kind']=='references')
appendix_start=next(x['physical_page'] for x in sections if x['kind']=='appendix')
summaries=[];text_pages=[];counts={'main':0,'appendix':0,'references':0,'prelim':0,'blank':0,'english':0}
english_start=next(i for i,p in enumerate(pdf,1) if 'University of Tehran' in p.get_text())
for i,page in enumerate(pdf,1):
    txt=page.get_text();words=txt.split()
    body_words=[w for w in page.get_text('words') if 95<=w[1]<=795]
    blank=not body_words
    kind='bismillah_reserved' if i==3 else 'defense_placeholder' if i==5 else 'blank' if blank else 'main' if main_start<=i<refs_start else 'references' if refs_start<=i<appendix_start else 'appendix' if appendix_start<=i<english_start else 'english' if i>=english_start else 'prelim'
    counts.setdefault(kind,0)
    counts[kind]+=1
    summaries.append({'page':i,'kind':kind,'words':len(words),'body_words':len(body_words),'head':txt[:180]})
    text_pages.append(f'---PAGE {i} ({kind})---\n'+txt)
meta.update({'pdf_pages':len(pdf),'counts':counts,'substantive_pages':counts['main']+counts['appendix'],'main_start':main_start,'refs_start':refs_start,'appendix_start':appendix_start,'page_summary':summaries})
(OUT/'pagination.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'rendered-text.txt').write_text('\n'.join(text_pages),encoding='utf-8')
images=OUT/'qa-pages';images.mkdir(exist_ok=True)
from PIL import Image,ImageDraw,ImageFont
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
for i,page in enumerate(pdf,1):
    path=images/f'page-{i:03d}.png'
    page.get_pixmap(matrix=pymupdf.Matrix(1.35,1.35)).save(str(path))
for start in range(0,len(pdf),12):
    sheet=Image.new('RGB',(1440,4*530),'#ECECEC');dr=ImageDraw.Draw(sheet)
    for j in range(start,min(start+12,len(pdf))):
        im=Image.open(images/f'page-{j+1:03d}.png');im.thumbnail((460,490))
        x=(j-start)%3*480+(480-im.width)//2;y=(j-start)//3*530+30
        sheet.paste(im,(x,y));dr.text((x,y-27),f'Page {j+1} / {summaries[j]["kind"]}',font=font,fill='black')
    sheet.save(images/f'contact-{start//12+1:02d}.jpg')
# OOXML structural verification after Word save.
with zipfile.ZipFile(DOCX) as z:
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    tree=etree.fromstring(z.read('word/document.xml'))
    par=tree.xpath('//w:body//w:p',namespaces=ns)
    persian=[p for p in par if re.search('[\u0600-\u06ff]',''.join(p.xpath('.//w:t/text()',namespaces=ns)))]
    rtl=[p for p in persian if p.xpath('./w:pPr/w:bidi[not(@w:val="0")]',namespaces=ns)]
    audit={'zip_ok':z.testzip() is None,'persian_paragraphs':len(persian),'explicit_rtl_paragraphs':len(rtl),'sections':len(tree.xpath('//w:sectPr',namespaces=ns)),'ltr_runs_explicit_or_default':len(tree.xpath('//w:r[w:rPr/w:rtl[@w:val="0"] or not(w:rPr/w:rtl)]',namespaces=ns)),'page_fields':sum(z.read(n).count(b'PAGE') for n in z.namelist() if n.startswith('word/header') or n.startswith('word/footer'))}
    (OUT/'ooxml-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
print(json.dumps({'pdf_pages':len(pdf),'counts':counts,'substantive':meta['substantive_pages'],'boundaries':[(x['title'],x['physical_page']) for x in sections]},ensure_ascii=False),flush=True)
