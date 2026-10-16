# -*- coding: utf-8 -*-
from pathlib import Path
import json,subprocess,sys
import win32com.client,pythoncom
R=Path(__file__).resolve().parent
DOC=R/'گزارش_پروژه_کارشناسی_ایمان_کربلائی.docx'
PDF=DOC.with_suffix('.pdf')
pythoncom.CoInitialize()
app=win32com.client.DispatchEx('Word.Application');app.Visible=False;app.DisplayAlerts=0
old_numeral=app.Options.ArabicNumeral
# Contextual numerals render PAGE and TOC fields with Persian digits in Persian paragraphs.
app.Options.ArabicNumeral=2
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
 word.Close(False);word=None
 bundled_python=Path(r'C:\Users\mandegar\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
 subprocess.run([str(bundled_python),str(R/'enforce_persian_rtl.py'),str(DOC)],check=True)
 word=app.Documents.Open(str(DOC),ConfirmConversions=False,ReadOnly=True,AddToRecentFiles=False)
 word.Repaginate()
 pages=word.ComputeStatistics(2)
 word.ExportAsFixedFormat(str(PDF),17,OpenAfterExport=False,OptimizeFor=0,CreateBookmarks=1)
 meta={'word_version':str(app.Version),'word_pages':pages,'main_start':start,'main_end':end,'toc_count':word.TablesOfContents.Count}
finally:
 if word is not None:word.Close(False)
 app.Options.ArabicNumeral=old_numeral
 app.Quit();pythoncom.CoUninitialize()
(R/'word-render-metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
