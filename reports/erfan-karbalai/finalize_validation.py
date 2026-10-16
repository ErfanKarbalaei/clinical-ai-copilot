"""Write the Persian validation report from final rendered evidence."""
from pathlib import Path
import json,sys,hashlib,subprocess,zipfile,re
from lxml import etree
import pymupdf
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.stdout.reconfigure(encoding='utf-8')
meta=json.loads((OUT/'pagination.json').read_text(encoding='utf-8'))
audit=json.loads((OUT/'ooxml-audit.json').read_text(encoding='utf-8'))
build=json.loads((OUT/'build-metadata.json').read_text(encoding='utf-8'))
docx=OUT/'گزارش_پروژه_کارشناسی_عرفان_کربالئی.docx';pdf=docx.with_suffix('.pdf')
counts=meta['counts'];total=meta['pdf_pages']
assert docx.exists() and pdf.exists()
assert audit['zip_ok']
assert counts['main']>=50
assert meta['word_pages']==total
assert all(s['physical_page']%2==1 and s['display_page']%2==1 for s in meta['sections'])
pages=pymupdf.open(pdf)
assert not pages[2].get_text().strip() and len(pages[2].get_images())==0
blank=[p['page'] for p in meta['page_summary'] if p['kind']=='blank']
# Check bounding boxes for clipping at the physical page edge.
edge=[]
for i,p in enumerate(pages,1):
    for w in p.get_text('words'):
        if w[0]<20 or w[2]>p.rect.width-20 or w[1]<20 or w[3]>p.rect.height-20:edge.append((i,w[4]))
assert not edge,edge[:5]
with zipfile.ZipFile(docx) as z:
    root=etree.fromstring(z.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    txt=' '.join(root.xpath('//w:t/text()',namespaces=ns))
    assert 'عرفان کربالئی' in txt
    assert 'STT_FALLBACK_PROVIDERS' in txt
    assert not root.xpath('//w:pBdr/w:bottom[@w:themeColor="accent1"]',namespaces=ns)
    assert 'هٔ' not in txt
    border_count=len(root.xpath('//w:tbl/w:tr[1]/w:trPr/w:tblHeader',namespaces=ns))
    section_types=root.xpath('//w:sectPr/w:type/@w:val',namespaces=ns)
    doc_paths=re.findall(r'https?://[^\s\u200e]+',txt)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
state=subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True).stdout
(OUT/'final-git-status.txt').write_text(state,encoding='utf-8')
(OUT/'artifact-hashes.json').write_text(json.dumps({'docx':sha(docx),'pdf':sha(pdf),'HEAD':head},indent=2),encoding='utf-8')
rows='\n'.join('| '+s['title']+' | '+str(s['physical_page'])+' | '+str(s['display_page'])+' |' for s in meta['sections'])
report=f'''# گزارش تطبیق و اعتبارسنجی

تاریخ نهایی بررسی: ۱۴ اکتبر ۲۰۲۶. نام دانشجو با تأیید صریح کاربر: **عرفان کربالئی**.

## تحویل و شمارش واقعی

- Word قابل ویرایش: `{docx}`
- پیش‌نمایش PDF: `{pdf}`
- کل سند: **{total} صفحهٔ واقعی**؛ تعداد در Microsoft Word 16.0 با `ComputeStatistics(wdStatisticPages)` و در PDF صادرشده با `len(pymupdf.open(...))` برابر بود.
- **{counts['main']} صفحهٔ محتوای فصل‌های اصلی**، بدون مقدمات، فهرست‌ها، منابع، پیوست‌ها و صفحات سفید. حداقل ۵۰ صفحه حتی بدون احتساب تمام پیوست‌ها حاصل شد.
- **{counts['appendix']} صفحهٔ پیوست فنی**؛ مجموع متن اصلی و پیوست‌های غیرسفید: **{meta['substantive_pages']} صفحه**.
- منابع: {counts['references']} صفحه؛ مقدمات و فهرست‌ها: {counts['prelim']} صفحه؛ جلد انگلیسی: {counts['english']} صفحه؛ محل صورت‌جلسه: ۱ صفحه؛ محل خالی بسم‌الله: ۱ صفحه؛ صفحات بدون محتوای بدنه: {counts['blank']} صفحه.
- متن اولیهٔ فصل‌ها و منابع در فایل نگارش {build['text_words']} واژه داشت؛ این عدد تخمین صفحه نیست. سند دارای {build['tables']} جدول مرجع/تحلیلی و {build['figures']} نمودار فنی است. تعداد بیشتر از هدف تقریبی ۵۵–۶۵ به دلیل پیوست کامل داده/API/تنظیمات/آزمون و صفحات الزامی چاپ دورو است؛ صفحات سفید برای حداقل طول شمرده نشده‌اند.

روش تفکیک صفحات: bookmark آغاز هر فصل از Word شمارهٔ فیزیکی و شمارهٔ نمایشی می‌گیرد. بازهٔ فصل‌ها و پیوست‌ها در `pagination.json` ثبت شده است. برای جدا کردن سفیدهای احتمالی، واژه‌های بدنه با مختصات عمودی ۹۵ تا ۷۹۵ پوینت بررسی شده و سرصفحه و شمارهٔ پایین کنار گذاشته شده‌اند. صفحهٔ ۳ و صفحهٔ ۵ به‌طور صریح محل بسم‌الله و صورت‌جلسه‌اند و در شمارش محتوای اصلی نیستند. صفحهٔ کوتاه فهرست، سفید محسوب نشده است. آغاز متن اصلی صفحهٔ فیزیکی {meta['main_start']}، منابع {meta['refs_start']} و پیوست‌ها {meta['appendix_start']} است.

صفحات بدون محتوای بدنه که از شمارش کنار گذاشته شدند: {', '.join(map(str,blank))}. این‌ها پشت صفحات مقدماتی، جداکنندهٔ لازم برای شروع فرد، یا پشت جلد انگلیسی‌اند. فقط صفحات مقرر شیوه‌نامه و section break فرد ایجاد شده‌اند.

## منابع اولیه و اختلاف نام‌ها

| نام مورد انتظار | منبع موجود و خوانده‌شده | وضعیت |
|---|---|---|
| proposal.docx | report-inputs/AI_Clinical_Copilot_Proposal_Task_Split_RTL_WORD_FIXED_V3.docx | پاراگراف‌ها و جدول تخصیص و زمان‌بندی استخراج و بررسی شد |
| report-format.pdf | report-inputs/BSc-project-report-format.pdf | سه صفحهٔ متن و نمودار صفحه‌آرایی بررسی شد |
| title-page-template.docx | report-inputs/BSc-project-report-cover-fa-1401.pdf | قالب Word موجود نیست؛ جلد قابل ویرایش از قالب PDF بازسازی شد |

پروپوزال نام‌ها را «عرفان کربلائی» و «ایمان کربلائی» نوشته است. کاربر نگارش «عرفان کربالئی» را برای دانشجوی صاحب گزارش تأیید کرد؛ نام همکار مطابق منبع باقی ماند. عنوان فارسی و انگلیسی پروژه، دانشگاه تهران، دانشکدگان فارابی، دانشکدهٔ مهندسی و استاد راهنما دکتر کاظم فولادی قلعه از منابع گرفته شدند. نگارش انگلیسی نام استاد حدس زده نشد و نام فارسی تأییدشده در جلد انگلیسی حفظ شده است.

## تطبیق قالب دانشگاه

- A4 به اندازهٔ ۲۱ × ۲۹٫۷ سانتی‌متر.
- متن فارسی B Nazanin چهارده پوینت، عنوان فصل بیست، بخش هجده، زیربخش شانزده؛ جدول‌ها دوازده و متن فنی لاتین درون آن‌ها حدود ده‌ونیم پوینت؛ کد Consolas ده پوینت. اندازهٔ متن اصلی برای افزایش طول تغییر نکرد.
- فاصلهٔ خطوط متن اصلی تک‌خطی، معادل `100%` در راهنما. راهنما هم‌زمان عبارت «حدود ۱ سانتی‌متر» دارد که با تک‌خطی چهارده پوینت یکسان نیست؛ مقدار صریح ۱۰۰٪ مبنا قرار گرفت و فاصلهٔ سطر یک‌سانتی‌متری مصنوعی اعمال نشد.
- از نمودار صفحهٔ دوم: حاشیهٔ داخلی ۲٫۵، خارجی ۲، پایین ۲ سانتی‌متر؛ سرصفحه در ۲٫۵ و آغاز ناحیهٔ بدنه در ۳٫۵ سانتی‌متر. mirrorMargins برای چاپ دورو فعال است.
- تمام فصل‌ها، منابع و پیوست‌ها با section از نوع oddPage آغاز می‌شوند. شماره‌ها پس از فهرست‌ها پیوسته‌اند و در شروع هر فصل از نو شروع نمی‌شوند. صفحات نخست فصل سرصفحه ندارند و PAGE در پایین وسط دارند؛ در صفحات دیگر شماره در گوشهٔ بیرونی و عنوان در گوشهٔ مقابل قرار دارد.
- فهرست مطالب و فهرست شکل‌ها و جدول‌ها field واقعی Word دارند و پیش از export به‌روزرسانی شدند. Heading style و bookmark برای پیمایش وجود دارند. عنوان جلد به‌صورت متن قابل ویرایش است و خط آبی ناخواستهٔ Title style حذف شد.
- پشت جلد فارسی، بسم‌الله، صورت‌جلسه، چکیده و جلد انگلیسی سفید است. تقدیم و سپاس اختیاری حذف شدند تا متن شخصی ساختگی اضافه نشود.
- **صفحهٔ بسم‌الله، صفحهٔ فیزیکی ۳، کاملاً خالی است**؛ نه عنوان، نه توضیح، نه caption و نه شماره و سرصفحه دارد. تصویر را می‌توان بعداً در همین محل افزود.

## RTL و ترکیب فارسی و لاتین

پاراگراف‌ها با `w:bidi` و متن فارسی با `w:rtl` و زبان `fa-IR` ساخته شدند. نام‌ها، pathها، شناسه‌ها و متغیرها run مستقل LTR دارند؛ کد و URL پاراگراف LTR است. Word برخی `w:rtl=0`ها را هنگام ذخیره حذف و از حالت پیش‌فرض LTR استفاده می‌کند؛ این حذف به معنی وارونه کردن دستی متن نیست.

در رندر نخست، جهت دیداری jc=right در پاراگراف bidi و فهرست Word مناسب نبود. یک سند آزمایشی جهت ساخته و در Word رندر شد؛ مقدار start برای تیترهای RTL و ReadingOrder راست‌به‌چپ برای TOC اعمال شد. شماره‌گذاری فصل‌ها نیز از حالت reset به ادامه اصلاح شد. ترکیب «هٔ» در قلم نصب‌شده دایرهٔ نقطه‌چین نشان می‌داد؛ در سند نمایشی به اضافهٔ درست «ه‌ی» تبدیل شد. متن انگلیسی جلد در خط مستقل و عبارت‌های چندواژه‌ای کوتاه با فاصلهٔ نشکن حفظ شدند.

پس از ذخیرهٔ Word، سلامت ZIP تأیید شد؛ {audit['persian_paragraphs']} پاراگراف حاوی فارسی و {audit['explicit_rtl_paragraphs']} پاراگراف با bidi صریح وجود داشت. تفاوت مربوط به بلوک‌های نمونهٔ JSON دارای متن فارسی در پاراگراف LTR است. {audit['ltr_runs_explicit_or_default']} run حالت صریح یا پیش‌فرض LTR داشت. جدول‌های بدنه RTL visual و {border_count} ردیف نخست دارای تکرار عنوان‌اند. خروجی از نظر قرار گرفتن متن در لبهٔ فیزیکی صفحه نیز بررسی شد؛ واژهٔ خارج از فاصلهٔ ایمنی ۲۰ پوینت دیده نشد.

## رندر و بازبینی دیداری

Word 16.0 واقعاً سند را باز کرد، فهرست‌ها را به‌روزرسانی کرد، repaginate انجام داد، ذخیره کرد و با ExportAsFixedFormat به PDF تبدیل نمود. PDF با PyMuPDF به تصویر تمام صفحات تبدیل شد. تمام صفحات در contact sheet برای عیب‌های درشت چیدمان مرور شدند؛ صفحات نماینده با تصویر بزرگ جدا بررسی شدند: جلد، صفحهٔ ۳، چکیده، فهرست‌ها، آغاز فصل، صفحهٔ فنی مخلوط، جدول API، جدول داده، نمودارها، منابع، کد و جلد انگلیسی. **بازبینی تمام صفحات در بزرگ‌نمایی ۱۰۰٪ ادعا نمی‌شود**؛ بررسی نماینده مطابق درخواست انجام شد و مرور thumbnail تمام صفحات مکمل آن بود.

نمونه‌های دشوار شامل FastAPI، PostgreSQL، OpenRouter، /api/v1/patients، path سرویس، STT_FALLBACK_PROVIDERS، STT_GOOGLE_MAX_CHUNK_SECONDS، مدل، parentheses و کد JSON بودند. حروف فارسی پیوسته، شناسه‌های لاتین به ترتیب اصلی، جدول‌ها در عرض صفحه و نمودارها بدون بریدگی در نمونه‌های بررسی‌شده دیده شدند. فهرست و شمارهٔ صفحات با آغاز bookmarkها تطبیق داده شد. برش نشان دانشگاه نیز از PDF قالب اصلاح شد. محدودیت renderer همراه مهارت با Word نصب‌شده جبران شد.

## ماتریس شواهد و پوشش محتوا

ماتریس `evidence-matrix.md` پیش از نگارش فصل‌ها ایجاد شد. ساختار گزارش ۱۲ فصل است و تمام محورهای خواسته‌شده را در این فصل‌ها پوشش می‌دهد: معرفی و مسئولیت، نیازمندی و مبانی، معماری، Backend و API و داده، Context و timeline، سند/OCR/تحلیل، provider و گفتگو، صوت، ایمنی و شواهد و MCP، امنیت، تست و استقرار، نتیجه و آینده. پیوست‌های API، فرهنگ داده، تنظیمات و آزمون از مسیر ثبت‌شدهٔ برنامه، metadata ORM، Settings و AST ساخته شده‌اند. کد استخراج متادیتا به پایگاه داده یا provider زنده وصل نمی‌شود.

نسخهٔ مبنا: `{head}` به همراه تغییرات موجود در config و stt و requirements و آزمون جدید هنگام شروع. مالکیت Backend/AI به عرفان، Frontend/UX به ایمان و معماری/E2E/Deployment به هر دو مطابق پروپوزال بیان شده است. نویسندهٔ commit به‌تنهایی مالکیت انحصاری تمام کد فرض نشده است.

ادعاهای مهم کنترل‌شده:

| موضوع | بیان دقیق در گزارش |
|---|---|
| استخراج سند | متن PDF/OCR و تحلیل متن؛ بدون ساخت خودکار فیلد Hb/WBC/glucose |
| timeline | مشتق از رکوردهای اصلی؛ اتکای انحصاری به ClinicalEvent ادعا نشده است |
| خلاصه بیمار | overview ساختاریافته؛ خلاصهٔ روایی مستقل AI ادعا نشده است |
| مدل‌ها | نام واقعی در کد ثبت شده؛ availability مدل‌های ایستا یا موفقیت live ادعا نشده است |
| ایمنی دارو | AI-first جاری و قواعد قدیمی مستقل؛ تفاوت با rule-only طرح اولیه روشن است |
| Citation | ID واقعی پرونده؛ اعتبار ID با حمایت معنایی از ادعا یکی دانسته نشده است |
| Retrieval | بدون PubMed/FDA/RxNorm و پایگاه برداری عملیاتی |
| MCP | شش ابزار و read-only در subprocess محلی، آزمایشی؛ دسترسی مستقیم ACL وب ندارد |
| امنیت | JWT/bcrypt/ACL واقعی؛ بدون ادعای انطباق یا امنیت کامل |
| استقرار | Docker/Nginx موجود؛ فقط HTTP در config فعلی و بدون تأیید استقرار عمومی |
| ارزیابی | هیچ WER/CER/SUS/P95 یا اثربخشی بالینی ساختگی درج نشده است |

منابع فنی از وب‌سایت رسمی FastAPI، SQLAlchemy، PostgreSQL، Next.js، Google، OpenRouter، Speechmatics، pypdf، Docker و OWASP بررسی شدند. منابع داخلی با منابع علمی بیرونی و با منابع پاسخ‌دهی خود سامانه تفکیک شده‌اند. شیوه‌نامه سبک خاص ارجاع را مقرر نکرده بود؛ شماره‌های یکتا و URL و تاریخ دسترسی استفاده شد. عنوان یا DOI یا مقالهٔ ساختگی اضافه نشده است.

## نتیجهٔ اجرای آزمون

فرمان واقعی:

```text
F:\\clinical-ai-copilot\\.venv\\Scripts\\python.exe -B reports\\erfan-karbalai\\run_verification.py
```

Python 3.12.2 و pytest 8.4.2. وابستگی pytest و SpeechRecognition فقط در `reports/erfan-karbalai/tooldeps` نصب شدند؛ requirements برنامه تغییر داده نشد. تعداد جمع‌آوری‌شده ۶۱، موفق ۵۹، خطای setup دو، skipped صفر؛ مدت ثبت‌شدهٔ pytest ۴۲٫۳۰ ثانیه. دو خطا در fixture فایل test_storage_service.py به رد اتصال MinIO در localhost:9000 مربوط بود و به موفق یا skipped تبدیل نشده است. خطای assertion برای ۵۹ تست دیگر ثبت نشد. ده warning شامل deprecation ابزارها بود.

هشت فایل منتخب: health، CORS، logging، storage، extraction، STT پایه، STT جدید و OpenRouter provider. تماس‌های AI/STT در تست‌ها mock بودند. تست‌های DB/API و E2E کامل برای این گزارش اجرا نشدند؛ نتیجهٔ تاریخی docs/task19 بازاجرای فعلی نامیده نشده است. Docker، migration و seed برای سبز کردن نتیجه اجرا نشدند و دادهٔ توسعه تغییر داده نشد. جزئیات رخدادهای خطا در XML خروجی از headerهای امضاشده و traceback حساس پاک شد؛ وضعیت آزمون‌ها حفظ شده است.

## موارد نیازمند تکمیل عرفان

۱. ماه و سال واقعی تحویل روی جلد فارسی و انگلیسی خالی است؛ سال تحصیلی پروپوزال تاریخ تحویل فرض نشده است.
۲. تصویر بسم‌الله را در صفحهٔ ۳ درج کنید؛ پشت آن سفید بماند. درج تصویر ممکن است pagination را تغییر دهد، پس پس از ویرایش دوباره فهرست و صفحه‌شماری را بررسی کنید.
۳. فرم رسمی صورت‌جلسه را پس از دریافت دانشگاه در صفحهٔ ۵ قرار دهید. هیچ امضا، داور، تاریخ دفاع، نمره یا تأیید ساختگی درج نشده است.
۴. شمارهٔ دانشجویی در منابع نبود و ساخته نشد؛ اگر دانشگاه آن را برای جلد یا نسخهٔ CD لازم می‌داند باید دستی تکمیل شود. قالب Word رسمی جلد نیز در ورودی نبود و معادل PDF مبنا شد.
۵. نتایج تست کامل پایگاه، MinIO، سرویس زنده و ارزیابی بالینی در اجرای حاضر فراهم نشدند. شکاف‌های دانلود رابط، ابزار ffmpeg در container، proxy صوت، پاک‌سازی موقت، log حساس و سازگاری upload با Nginx در متن توضیح داده شده‌اند.
۶. صفحه‌بندی در نسخهٔ Word یا قلم متفاوت می‌تواند تغییر کند؛ PDF تحویلی مرجع شمارش این نسخه است. برای چاپ، از فهرست به بعد دورو و بدون حذف سفیدهای الزامی چاپ شود.
۷. صفحهٔ جداکنندهٔ فیزیکی ۱۸ محتوای بدنه ندارد ولی سرصفحهٔ فهرست روی آن باقی مانده است؛ در حداقل ۵۰ صفحه حساب نشده است. برای نسخهٔ صحافی، این صفحه را به‌صورت کاملاً سفید چاپ یا سرصفحهٔ آن را در Word حذف کنید. صفحات پشت جلد و بسم‌الله و صورت‌جلسه و چکیده و جلد انگلیسی کاملاً سفیدند.

## بهداشت مخزن و بازتولید

فایل‌های برنامه، منابع ورودی و گزارش‌های قبلی report_builder بازنویسی نشدند؛ هیچ commit یا push یا reset یا clean انجام نشد. تغییرات قبلی working tree باقی ماندند. سند جدید docs/medical-reference-mcp-report-fa.md نیز هنگام بررسی نهایی مشاهده شد؛ این سند پیشنهاد آینده بود و تغییر اجرایی Retrieval را ثابت نمی‌کرد؛ به آن دست زده نشد.

ابزارهای همراه workspace در loader پیکربندی نشده بودند و render_docx.py بستهٔ مهارت در مسیر مورد انتظار موجود نبود. به‌جای ادعای استفاده از آن، ابزارهای موجود Python/docx/OOXML و Microsoft Word واقعی به کار رفتند. helperها در همین پوشه‌اند: inspect_sources.py برای استخراج منابع، build_report.py و report_appendices.py برای ساخت، run_verification.py برای آزمون موجود، render_and_audit.py برای Word/PDF/تصویر، direction_probe.py برای بررسی رفتار جهت و finalize_validation.py برای ثبت این گزارش. تصویرهای QA و فایل‌های واسط صرفاً برای بررسی نگهداری شده‌اند.

SHA-256 سند نهایی: `{sha(docx)}`

SHA-256 PDF نهایی: `{sha(pdf)}`

## شمارهٔ آغاز بخش‌ها

| بخش | صفحهٔ فیزیکی PDF | شمارهٔ نمایشی Word |
|---|---:|---:|
{rows}
'''
(OUT/'گزارش_تطبیق_و_اعتبارسنجی.md').write_text(report,encoding='utf-8')
print('Validation saved. Word/PDF',total,'main',counts['main'],'appendix',counts['appendix'],'blank',counts['blank'])
