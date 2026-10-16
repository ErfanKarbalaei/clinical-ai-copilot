"""Update Word-generated contents, save, export PDF, and rasterize every page."""
from pathlib import Path
import json, sys, time
import pythoncom
import win32com.client
import fitz
sys.stdout.reconfigure(encoding="utf-8")
OUT=Path(__file__).resolve().parent
DOCX=OUT/"گزارش_پروژه_کارشناسی_عرفان_کربلائی_خلاصه‌شده.docx"
PDF=DOCX.with_suffix(".pdf")
PAGES=OUT/"qa-pages"
PAGES.mkdir(exist_ok=True)
wdFormatPDF=17
wdStatisticPages=2
word=None; doc=None
pythoncom.CoInitialize()
try:
    word=win32com.client.DispatchEx("Word.Application")
    word.Visible=False
    word.DisplayAlerts=0
    doc=word.Documents.Open(str(DOCX),ReadOnly=False,AddToRecentFiles=False,ConfirmConversions=False)
    doc.Fields.Update()
    for toc in doc.TablesOfContents:
        toc.Update()
    for tof in doc.TablesOfFigures:
        tof.Update()
    # Word stores running-head STYLEREF fields in separate header/footer stories.
    for section in doc.Sections:
        for index in (1, 2, 3):
            section.Headers(index).Range.Fields.Update()
            section.Footers(index).Range.Fields.Update()
    doc.Fields.Update()
    doc.Repaginate()
    pages=int(doc.ComputeStatistics(wdStatisticPages))
    doc.Save()
    doc.ExportAsFixedFormat(str(PDF),wdFormatPDF)
    print("WORD_PAGES",pages)
finally:
    if doc is not None: doc.Close(SaveChanges=True)
    if word is not None: word.Quit()
    pythoncom.CoUninitialize()

pdf=fitz.open(PDF)
for old in PAGES.glob("page-*.png"):
    old.unlink()
for i,page in enumerate(pdf,1):
    pix=page.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False)
    pix.save(PAGES/f"page-{i:03d}.png")
pages_text=[p.get_text() for p in pdf]
metadata={
 "word_pages":pages,"pdf_pages":len(pdf),"source":str(DOCX),"pdf":str(PDF),
 "rendered_pages":len(list(PAGES.glob("page-*.png"))),
 "appendix_a_pages":[i+1 for i,t in enumerate(pages_text) if "پیوست الف. مسیرهای منتخب رابط" in t],
 "appendix_b_pages":[i+1 for i,t in enumerate(pages_text) if "پیوست ب. تنظیمات منتخب اجرا" in t],
 "english_title_pages":[i+1 for i,t in enumerate(pages_text) if "University of Tehran" in t],
 "bismillah_pages":[i+1 for i,t in enumerate(pages_text) if "لم" in t and len(t.strip())<10],
 "texts":pages_text
}
(OUT/"render-metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
print("PDF_PAGES",len(pdf),"PNG_PAGES",metadata["rendered_pages"])
print("APPENDIX_A",metadata["appendix_a_pages"],"APPENDIX_B",metadata["appendix_b_pages"])
print("ENGLISH",metadata["english_title_pages"])
