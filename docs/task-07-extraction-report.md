# گزارش تسک ۷ — استخراج متن اسناد (PDF + OCR قطعی، بدون هوش مصنوعی)

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۷ (Task 7) — استخراج متن قطعی از اسناد + UI اسناد در فرانت‌اند
- **تاریخ اجرا:** 2026-08-26
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۹۲ تست + E2E فایل واقعی + SSR)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) قابلیت‌های فرانت‌اند

بخش جدید «اسناد» در پروندهٔ بیمار (`/patients/[id]`):
- **بارگذاری سند** (دیالوگ: انتخاب فایل PDF/تصویر/متن، عنوان، نوع سند)
- **نمایش وضعیت پردازش** با Badge فارسی: «در انتظار پردازش» / «در حال پردازش» (با انیمیشن pulse) / «متن استخراج شد» / «پردازش ناموفق»
- **دانلود فایل اصلی** (لینک مستقیم به presigned URL)
- **مشاهدهٔ متن استخراج‌شده** (دیالوگ — فقط وقتی extraction موفق بوده)
- **پردازش مجدد** (دکمهٔ تلاش دوباره روی اسناد ناموفق) و **حذف** با تأیید

## ۲) معماری پردازش

```
Upload (multipart) ──► 201 + extraction_status=pending
        └─(پاسخ ارسال شد)─► BackgroundTask: process_document
                                ├─ status=processing → commit
                                ├─ storage.get_object_bytes (MinIO)
                                ├─ extraction.extract_text (قطعی)
                                └─ status=completed/failed → commit
```
- `POST /documents/{id}/extract` → 202 (اجرای مجدد؛ 409 اگر در حال پردازش)
- **Race-safe:** حذف هم‌زمان سند وسط پردازش → rollback و لاگ، بدون کرش (`StaleDataError` مدیریت شد — این باگ در E2E واقعی پیدا و رفع شد)
- بدون صف/worker جدید — همان `BackgroundTasks` فریم‌ورک (اصل «بدون زیرساخت اضافه»)

## ۳) رویکرد PDF

`pypdf` → متن لایهٔ متنی هر صفحه؛ اگر مجموع متن < ۵۰ کاراکتر (سند اسکن‌شده) → OCR روی **تصاویر جاسازی‌شدهٔ صفحات** (بدون نیاز به poppler/render). سقف دفاعی ۵۰ صفحه.

## ۴) رویکرد OCR

`pytesseract` (Tesseract 5.5.3 نصب user-space با scoop + دادهٔ `fas+eng`) — **اختیاری و خودکشف**: بدون باینری، PDFهای متنی کار می‌کنند و اسکن/تصویر → failed با دلیل ثبت‌شده در لاگ. زبان: `fas+eng` در صورت وجود، وگرنه کاهش تدریجی. محدودیت شناخته‌شده: خروجی OCR فارسی ممکن است ترتیب حروف معکوس داشته باشد (رفتار شناخته‌شدهٔ Tesseract RTL) — متن کامل است ولی کیفیت فارزی به مدل و تصویر وابسته است.

## ۵) endpointها

جدول تسک ۶ + `POST /api/v1/documents/{id}/extract` (202/404/409). پاسخ آپلود همچنان `pending` است و کلاینت با GET وضعیت نهایی را می‌گیرد.

## ۶) تست‌ها و نتایج

- **۱۲ تست جدید** → مجموع **۹۲ passed, 0 skipped**: سرویس استخراج (۷ — شامل OCR انگلیسی و **فارسیِ واقعی** روی تصویر رندرشده) + API (۵ — چرخهٔ وضعیت، استخراج inline متن/PDF، شکست ذخیره‌سازی، re-extract)
- فرانت‌اند: `tsc --noEmit` ✅ و `next build` ✅
- E2E واقعی (`scripts/e2e_extraction.py`) — همه سبز:
```
1) text PDF  → completed | extracted: CLINICAL LAB REPORT WITH DETAILED PATIEN …
2) Persian image OCR → completed | extracted: ینیلاب هاگ‌ش‌یام زا ش‌رازگ   (متن کامل، ترتیب RTL معکوس)
3) blank PDF  → completed | text: ''   (بدون لایه/تصویر → متن نازک نگه داشته شد)
4) original file unchanged after processing ✓ (بایت‌به‌بایت)
5) re-extract: 202 → completed ✓   |   cleanup ✓
```
- **SSR تأیید شد** (سرور پروداکشن روی پورت ۳۱۰۰): بخش «اسناد» + «متن استخراج شد» (بیمار ۸) + «در انتظار پردازش» (سند seed بیمار ۱۰) + دانلود — سپس سند تستی حذف شد (204)

## ۷) راستی‌آزمایی با فایل واقعی

PDF واقعی با لایهٔ متنی (ساخته‌شده با xref صحیح)، تصویر PNG با متن فارسی رندرشده با فونت Tahoma (ویندوز)، PDF خالی شبیه اسکن — هر سه از مسیر کامل upload→MinIO→extraction→metadata→SSR رفتند.

## ۸) فایل‌ها

**ساخته‌شده:** `services/extraction.py` · `services/documents.py` · `tests/test_extraction_service.py` · `tests/pdf_helper.py` · `scripts/e2e_extraction.py` · `components/patients/document-actions.tsx` · گزارش
**تغییریافته:** `services/storage.py` (+get_object_bytes) · `routes/documents.py` (BackgroundTasks + extract + delete مقاوم) · `config.py` (+TESSERACT_CMD) · `requirements.txt` (+pypdf, pytesseract, Pillow, python-multipart) · فرانت‌اند: types/format/api + صفحهٔ بیمار · READMEها

## ۹) هشدارها

1. **سرورهای dev خودتان (PyCharm) در طول این تسک کهنه شدند** (ویرایش‌های سریع + reload → سرو کد قدیمی): درخت uvicorn--reload روی ۸۰۰۰ پاک و بعد خودش با کد جدید بالا آمد (E2E از روی همان پاسخ گرفت)؛ **سرور Next dev روی ۳۰۰۰ هنوز کد قدیمی صفحهٔ بیمار را نشان می‌دهد — یک‌بار restart کنید.**
2. OCR فارسی: ترتیب حروف خروجی گاهی معکوس است (محدودیت Tesseract fas) — نیاز به پس‌پردازش دارد؛ کیفیت به کیفیت تصویر وابسته است.
3. Tesseract به‌صورت user-space (scoop) نصب شد؛ مسیر در `.env` محلی (`TESSERACT_CMD`) تنظیم شد — روی ماشین‌های دیگر باید نصب/تنظیم شود (README بک‌اند).
4. استخراج synchronous در BackgroundTask است — فایل‌های OCR سنگین درخواست‌های دیگر را کند نمی‌کنند (بعد از پاسخ اجرا می‌شود) ولی برای فایل‌های بسیار بزرگ، صف کار فاز آینده است.
5. هیچ منطق AI/RAG/STT/ایمنی اضافه نشد — فقط ابزارهای قطعی (pypdf/Tesseract)؛ git diff بازبینی شد.

## ۱۰) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**. پیشنهاد تسک ۸: یادداشت‌های صوتی و تبدیل گفتار به متن فارسی (STT آماده) یا صفحهٔ تایم‌لاین بیمار.
