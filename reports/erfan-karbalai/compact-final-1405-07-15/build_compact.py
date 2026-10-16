"""Create a shorter, editable report from the latest reviewed DOCX."""
from pathlib import Path
import re
import sys
from copy import deepcopy
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Cm, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = next(ROOT.glob("*بازبینی‌شده.docx"))
OUTPUT = HERE / "گزارش_پروژه_کارشناسی_عرفان_کربلائی_خلاصه‌شده.docx"
USER_IMAGE = Path(r"C:\Users\mandegar\AppData\Local\Temp\codex-clipboard-da72b361-68c5-4a39-84ec-7551fcd2116c.png")
LOGO = HERE / "بسم‌الله.png"
OLD_NAME = "عرفان کربالئی"
NEW_NAME = "عرفان کربلائی"

def clean(s):
    return s.replace("\u200e", "").replace("\u200f", "").replace("\u2066", "").replace("\u2069", "")

def set_run_dir(run, rtl, lang="fa-IR"):
    rpr = run._element.get_or_add_rPr()
    tag = "w:rtl"
    el = rpr.find(qn(tag))
    if el is None:
        el = OxmlElement(tag)
        rpr.append(el)
    if rtl:
        el.set(qn("w:val"), "1")
    else:
        el.set(qn("w:val"), "0")
    lang_el = rpr.find(qn("w:lang"))
    if lang_el is None:
        lang_el = OxmlElement("w:lang")
        rpr.append(lang_el)
    lang_el.set(qn("w:val"), lang)
    lang_el.set(qn("w:eastAsia"), lang)

def set_para_dir(p, rtl=True):
    ppr = p._p.get_or_add_pPr()
    bidi = ppr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        ppr.append(bidi)
    bidi.set(qn("w:val"), "1" if rtl else "0")
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl else WD_ALIGN_PARAGRAPH.LEFT

def replace_in_runs(p, old, new):
    n = 0
    for r in p.runs:
        if old in r.text:
            n += r.text.count(old)
            r.text = r.text.replace(old, new)
    return n

def replace_paragraph(p, old, new):
    full = "".join(r.text for r in p.runs)
    if old not in full:
        return 0
    start = full.index(old)
    end = start + len(old)
    offset = 0
    first = last = None
    for i,r in enumerate(p.runs):
        lo, hi = offset, offset + len(r.text)
        if lo <= start < hi or (start == hi == lo):
            first = i
        if lo < end <= hi:
            last = i
        offset = hi
    if first is None or last is None:
        return 0
    offsets=[];offset=0
    for r in p.runs:
        offsets.append((offset,offset+len(r.text)));offset+=len(r.text)
    a0,a1=offsets[first];b0,b1=offsets[last]
    before=p.runs[first].text[:start-a0]
    after=p.runs[last].text[end-b0:]
    if first==last:
        p.runs[first].text=before+new+after
    else:
        p.runs[first].text=before+new
        for r in p.runs[first+1:last]:r.text=""
        p.runs[last].text=after
    return 1

def replace_first_run(p, text):
    runs = p.runs
    if not runs:
        p.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""

def add_p(text, style="Normal", rtl=True, bold=False, size=None, before=0, after=6):
    p = doc.add_paragraph(style=style)
    set_para_dir(p, rtl)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(text)
    r.bold = bold
    set_run_dir(r, rtl)
    if size:
        r.font.size = Pt(size)
    return p

def set_cell_text(cell, text, rtl=True, header=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_together = True
    set_para_dir(p, rtl)
    if not rtl:
        if text.startswith(("GET ", "POST ", "PATCH ", "DELETE ")):
            text = text.replace("/", "/\u200e")
        spans=[("\u202A" + text + "\u202C",False)]
    else:
        spans=[]
        for part in re.split(r"([A-Za-z][A-Za-z0-9_.:/{}?=+-]*)", text):
            if part:
                spans.append((part, bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:/{}?=+-]*",part))))
    for content,is_ltr in spans:
        r = p.add_run(content)
        r.bold = header
        set_run_dir(r, not is_ltr, "en-US" if is_ltr else "fa-IR")
        r.font.name = "Times New Roman" if is_ltr else "B Nazanin"
        r.font.size = Pt(9.5 if is_ltr else 10.5)
        r._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), r.font.name)

def style_table(table, widths_cm, header):
    table.style = "Table Grid"
    tblpr = table._tbl.tblPr
    bidi = tblpr.find(qn("w:bidiVisual"))
    if bidi is None:
        tblpr.append(OxmlElement("w:bidiVisual"))
    table.autofit = False
    for row_i, row in enumerate(table.rows):
        if row_i == 0 and header:
            trpr = row._tr.get_or_add_trPr()
            repeat = OxmlElement("w:tblHeader")
            repeat.set(qn("w:val"), "true")
            trpr.append(repeat)
        for i, cell in enumerate(row.cells):
            cell.width = Cm(widths_cm[i])
            tcpr = cell._tc.get_or_add_tcPr()
            tcw = tcpr.find(qn("w:tcW"))
            if tcw is not None:
                tcw.set(qn("w:w"), str(round(widths_cm[i] * 567)))
                tcw.set(qn("w:type"), "dxa")
            mar = tcpr.find(qn("w:tcMar"))
            if mar is None:
                mar = OxmlElement("w:tcMar")
                tcpr.append(mar)
            for edge in ("top", "start", "bottom", "end"):
                el = mar.find(qn("w:" + edge))
                if el is None:
                    el = OxmlElement("w:" + edge)
                    mar.append(el)
                el.set(qn("w:w"), "70")
                el.set(qn("w:type"), "dxa")
            if row_i == 0:
                shd = tcpr.find(qn("w:shd"))
                if shd is None:
                    shd = OxmlElement("w:shd")
                    tcpr.append(shd)
                shd.set(qn("w:fill"), "D9D9D9")

def add_table(rows, widths_cm):
    tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
    for ri, row in enumerate(rows):
        for ci, value in enumerate(row):
            is_ltr = (ci == 0 and (value.startswith(("GET ", "POST ", "PATCH ", "DELETE ", "AI_", "STT_", "MINIO_", "POSTGRES_", "NEXT_PUBLIC_"))))
            if ci == len(row)-1 and value and value[:1].isascii() and value[:1].isalnum() and not value.startswith(("GET ", "POST ", "PATCH ", "DELETE ")):
                is_ltr = True
            set_cell_text(tbl.cell(ri, ci), value, rtl=not is_ltr, header=(ri == 0))
    style_table(tbl, widths_cm, True)
    return tbl

def make_logo_image():
    im = Image.open(USER_IMAGE).convert("RGB")
    pixels = im.load()
    xs, ys = [], []
    # Ignore the thin black screenshot frame, then crop to the actual calligraphy
    # with a modest white margin so the emblem is legible on the reserved page.
    inset_x, inset_y = round(im.width * 0.025), round(im.height * 0.025)
    for y in range(inset_y, im.height-inset_y):
        for x in range(inset_x, im.width-inset_x):
            r, g, b = pixels[x, y]
            if min(r, g, b) < 160:
                xs.append(x); ys.append(y)
    if not xs:
        raise ValueError("Attached Bismillah artwork has no dark pixels")
    margin = round(max(im.width, im.height) * 0.035)
    box = (max(0, min(xs)-margin), max(0, min(ys)-margin),
           min(im.width, max(xs)+margin+1), min(im.height, max(ys)+margin+1))
    im.crop(box).save(LOGO, quality=95)
    return box

doc = Document(SOURCE)

# Correct the Persian author spelling without changing the English transliteration.
for p in doc.paragraphs:
    replace_in_runs(p, OLD_NAME, NEW_NAME)
for t in doc.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                replace_in_runs(p, OLD_NAME, NEW_NAME)

# Replace the two known submission placeholders with the supplied exact date.
p_fa = next(p for p in doc.paragraphs if clean(p.text).strip() == "ماه و سال تحویل: ................")
p_fa.clear()
set_para_dir(p_fa, True)
p_fa.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p_fa.add_run("ماه و سال تحویل: ۱۵ مهر ۱۴۰۵ ")
set_run_dir(r, True); r.font.name = "B Nazanin"; r.font.size = Pt(14)
r = p_fa.add_run("(۱۵ اکتبر ۲۰۲۶)")
set_run_dir(r, False, "fa-IR"); r.font.name = "B Nazanin"; r.font.size = Pt(14)
p_en = next(p for p in doc.paragraphs if p.text.strip() == "Submission month and year: ................")
replace_first_run(p_en, "Submission month and year: 15 Mehr 1405 (15 October 2026)")
set_para_dir(p_en, False)
for r in p_en.runs:
    set_run_dir(r, False, "en-US")

# Keep the image-only Bismillah page and insert the supplied image after its page break.
box = make_logo_image()
bism_p = doc.paragraphs[13]
assert clean(bism_p.text).strip() == "" and bism_p._p.xpath(".//w:br[@w:type='page']")
set_para_dir(bism_p, False)
bism_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
bism_p.paragraph_format.space_before = Pt(145)
bism_p.paragraph_format.space_after = Pt(0)
bism_p.paragraph_format.line_spacing = 1
bism_p.add_run().add_picture(str(LOGO), width=Inches(6.0))

# Remove the four bibliography-only internal references. The remaining ten cited
# references already form a continuous 1-10 sequence; no in-text renumbering is needed.
deleted_refs = []
for p in list(doc.paragraphs):
    s = clean(p.text).strip()
    m = re.match(r"^\[\s*([0-9۰-۹]{1,2})\s*\]", s)
    if m and int(m.group(1).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))) in {11,12,13,14}:
        deleted_refs.append(s[:30])
        p._element.getparent().remove(p._element)
assert len(deleted_refs) == 4, deleted_refs

# Replace references to exhaustive appendices with the new focused scope.
rewrites = [
    ("شناسه‌ی توابع و فایل‌ها در فصل‌های فنی و پیوست‌ها آورده شده‌اند تا شرح معماری قابل پیگیری باشد.",
     "شناسه‌ی توابع و فایل‌ها در فصل‌های فنی آمده‌اند؛ پیوست الف مسیرهای منتخب و پیوست ب تنظیمات مهم اجرا را خلاصه می‌کند."),
    ("پیوست‌ها مرجع قراردادهای واقعی، فرهنگ داده و تنظیمات‌اند؛ خواننده برای فهم استدلال اصلی به خواندن تمام جزئیات آن‌ها نیاز ندارد، اما برای بازبینی فنی می‌تواند به آن‌ها رجوع کند.",
     "دو پیوست پایانی فقط مسیرهای منتخب رابط و تنظیمات مهم اجرا را گرد می‌آورند؛ شرح معماری و داده در فصل‌های اصلی آمده است."),
    ("فرمان و آرگومان‌های اجرا در گزارش تغییرات و اعتبارسنجی ثبت شده‌اند؛ جزئیات هر مورد نیز در پیوست ث آمده است.",
     "فرمان و آرگومان‌های مؤثر اجرا در گزارش اعتبارسنجی ثبت شده‌اند؛ جدول فصل حاضر دامنه‌ی نتیجه‌ها را نشان می‌دهد."),
    ("مثال فرمان‌ها در پیوست آمده",
     "تنظیمات منتخب در پیوست ب خلاصه شده‌اند"),
]
for old,new in rewrites:
    found = 0
    for p in doc.paragraphs:
        found += replace_paragraph(p, old, new)
    assert found == 1, (old, found)

# Remove Appendix 11-14 style prose from the opening paragraph of the bibliography.
for p in doc.paragraphs:
    if "گزارش‌های تسک‌های داخلی با دامنه و تاریخ اجرای خود تفسیر می‌شوند" in p.text:
        found = replace_paragraph(p, "و گزارش‌های تسک‌های داخلی با دامنه و تاریخ اجرای خود تفسیر می‌شوند", "و شواهد مخزن و نتایج آزمون نیز در فصل‌های مربوط توضیح داده شده‌اند")
        assert found == 1

# Delete all five long appendices and their exhaustive inventories. Preserve the
# section-break paragraph immediately before the English title page.
body = doc.element.body
nodes = list(body)
from docx.text.paragraph import Paragraph
start_i = next(i for i,n in enumerate(nodes) if n.tag == qn("w:p") and
               Paragraph(n, doc).style.name == "Heading 1" and
               clean(Paragraph(n, doc).text).strip().startswith("پیوست الف. مرجع مسیرهای رابط"))
cover_i = next(i for i,n in enumerate(nodes) if n.tag == qn("w:p") and "University of Tehran" in "".join(n.itertext()))
sect_i = max(i for i,n in enumerate(nodes[:cover_i]) if n.tag == qn("w:p") and n.xpath(".//w:sectPr"))
assert start_i < sect_i < cover_i
sect_boundary = nodes[sect_i]
for node in nodes[start_i:sect_i]:
    body.remove(node)

# Add only concise reference material: seven representative routes and seven
# high-impact environment settings. No exhaustive schemas or proposed tests.
appendix_nodes = []
h = add_p("پیوست الف. مسیرهای منتخب رابط برنامه‌نویسی (API)", "Heading 1", rtl=True, after=8)
h.paragraph_format.page_break_before = True
appendix_nodes.append(h._p)
p = add_p("این نمونه‌ها مسیرهای اصلی ساخت پرونده، ساخت زمینه، پردازش سند و گفتگوی بالینی را نشان می‌دهند. فهرست کامل مسیرها و قراردادهای OpenAPI در مخزن نگهداری می‌شود و برای پرهیز از تکرار در این گزارش بازنشر نشده است.", rtl=True, after=6)
appendix_nodes.append(p._p)
p = add_p("جدول الف-۱. مسیرهای منتخب API", "ReportTable", rtl=True, after=3)
appendix_nodes.append(p._p)
rows = [
    ["مسیر منتخب", "کارکرد در گردش کار"],
    ["POST /api/v1/patients", "ایجاد پرونده‌ی بیمار"],
    ["GET /api/v1/patients\n/{patient_id}/context", "ساخت زمینه از رکوردهای پرونده"],
    ["GET /api/v1/patients\n/{patient_id}/timeline", "خواندن خط زمانی مشتق‌شده"],
    ["POST /api/v1/patients\n/{patient_id}/documents", "بارگذاری سند برای یک بیمار"],
    ["POST /api/v1/documents\n/{document_id}/analyze", "تحلیل اختیاری سند ثبت‌شده"],
    ["POST /api/v1/patients\n/{patient_id}/chat", "گفتگوی بدون ماندگاری"],
    ["POST /api/v1/patients\n/{patient_id}/conversations", "ساخت گفتگوی ماندگار"],
]
t = add_table(rows, [8.6, 7.4])
appendix_nodes.append(t._tbl)

h = add_p("پیوست ب. تنظیمات منتخب اجرا", "Heading 1", rtl=True, before=12, after=8)
h.paragraph_format.page_break_before = True
appendix_nodes.append(h._p)
p = add_p("این جدول فقط متغیرهایی را گرد می‌آورد که برای انتخاب سرویس، اتصال ذخیره‌ساز یا نشانی رابط اهمیت مستقیم دارند. مقدارهای محرمانه در این گزارش درج نشده‌اند؛ مقدار نهایی باید با فایل محیط و پیکربندی همان استقرار تطبیق داده شود.", rtl=True, after=6)
appendix_nodes.append(p._p)
p = add_p("جدول ب-۱. متغیرهای منتخب و حدود تفسیر", "ReportTable", rtl=True, after=3)
appendix_nodes.append(p._p)
rows = [
    ["متغیر", "نقش و نکته‌ی پیاده‌سازی"],
    ["POSTGRES_DB", "نام پایگاه داده؛ fixture آزمون نام جداگانه دارد."],
    ["MINIO_ENDPOINT", "نشانی ذخیره‌ساز؛ باید برای مرورگر قابل دسترسی باشد."],
    ["STT_PROVIDER", "انتخاب سرویس پیش‌فرض گفتار از تنظیمات."],
    ["STT_FALLBACK_PROVIDERS", "ترتیب جایگزین‌های گفتار؛ زنجیره با موفقیت یا خطای نهایی متوقف می‌شود."],
    ["AI_PROVIDER", "انتخاب ارائه‌دهنده‌ی مدل؛ باید با شناسه‌ی مدل و کلید سازگار باشد."],
    ["AI_MODEL", "شناسه‌ی مدل متنی؛ به‌تنهایی دسترس‌پذیری یا ارزیابی بالینی را ثابت نمی‌کند."],
    ["NEXT_PUBLIC_API_URL", "نشانی API در رابط وب؛ هنگام build وارد bundle فرانت‌اند می‌شود."],
]
t = add_table(rows, [7.0, 9.0])
appendix_nodes.append(t._tbl)

# Move the newly authored appendix elements immediately before the retained
# section boundary, keeping the English title page and university pagination.
for node in appendix_nodes:
    sect_boundary.addprevious(node)

# Replace the old appendix running-head text cached in the shared appendix
# section. A neutral label remains correct across both concise appendices.
for section in doc.sections:
    for part in (section.header, section.even_page_header, section.first_page_header):
        for text_node in part._element.xpath(".//w:t"):
            if "پیوست ث. مرجع آزمون و سناریوهای تکمیلی" in (text_node.text or ""):
                text_node.text = "پیوست‌های فنی منتخب"

doc.core_properties.title = "گزارش پروژه کارشناسی عرفان کربلائی"
doc.core_properties.subject = "نسخه‌ی خلاصه‌شده با اصلاح جلد، صفحه‌ی بسم‌الله و مراجع"
doc.save(OUTPUT)
print("Saved", OUTPUT)
print("Source", SOURCE)
print("Bismillah crop", box, "size", Image.open(LOGO).size)
print("Removed bibliography entries", deleted_refs)
print("Paragraphs", len(doc.paragraphs), "tables", len(doc.tables), "pictures", len(doc.inline_shapes))
