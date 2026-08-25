# گزارش تسک ۶ — اسناد بیمار (بارگذاری + ذخیره‌سازی MinIO)

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۶ (Task 6) — API اسناد بیمار با ذخیرهٔ «اصل فایل» در object storage
- **تاریخ اجرا:** 2026-08-26
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۸۰ تست + E2E زنده با MinIO واقعی)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) endpointهای ساخته‌شده

| متد | مسیر | توضیح | کدها |
| --- | --- | --- | --- |
| POST | `/api/v1/patients/{id}/documents` | آپلود multipart: `file` + `title`/`doc_type` اختیاری — فایل اصلی دست‌نخورده در MinIO ذخیره می‌شود + رویداد تایم‌لاین | 201/404/422/503 |
| GET | `/api/v1/patients/{id}/documents` | فهرست اسناد بیمار (جدیدترین اول) | 200/404 |
| GET | `/api/v1/documents/{id}` | فرادادهٔ سند (بدون `storage_key` — جزئیات داخلی) | 200/404 |
| GET | `/api/v1/documents/{id}/download` | ریدایرکت 307 به presigned URL یک‌ساعته — خود MinIO فایل را سرو می‌کند | 307/404/503 |
| PATCH | `/api/v1/documents/{id}` | فقط فراداده (عنوان/نوع) — فایل اصلی هرگز تغییر نمی‌کند | 200/404 |
| DELETE | `/api/v1/documents/{id}` | حذف فایل از MinIO + فراداده + رویداد تایم‌لاین | 204/404/503 |

اعتبارسنجی: PDF/PNG/JPEG/WebP/text، حداکثر ۲۰MB، فایل خالی رد؛ پیام‌های 422/404 فارسی؛ خطای ذخیره‌سازی → **503**.

## ۲) فایل‌های ساخته/تغییریافته

**ساخته‌شده:** `app/services/storage.py` (کلاینت MinIO + کلید یکتا + upload/presign/delete) · `app/schemas/document.py` · `app/api/v1/routes/documents.py` · `tests/test_documents_api.py` (۱۵ تست با storage فیک‌شده) · `tests/test_storage_service.py` (۲ تست یکپارچه با MinIO واقعی، skip خودکار) · `scripts/e2e_documents.py` (راستی‌آزمایی زنده) · همین گزارش
**تغییریافته:** `app/core/config.py` (تنظیمات MINIO_*) · `app/api/v1/api.py` · `requirements.txt` (+`minio`, +`python-multipart`) · `backend/README.md` · `README.md` ریشه · `docs/README.md`
**بدون تغییر schema دیتابیس** — جدول `documents` تسک ۲ همین ساختار را داشت (storage_key/extraction_status/extracted_text).

## ۳) تست‌ها و نتیجه

۱۷ تست جدید → مجموع: **۸۰ passed** (4.7s). تست‌های API بدون MinIO اجرا می‌شوند (storage فیک با monkeypatch)؛ تست‌های storage روی MinIO واقعی اجرا و در نبود آن skip می‌شوند.

## ۴) نتیجهٔ E2E زنده (خروجی واقعی `scripts/e2e_documents.py`)

```
1) upload 201: آزمایش خون — تست زنده | application/pdf | 40 bytes | pending
2) list: 2 documents, new doc present, newest-first
3) download: 307 → presigned → byte-identical roundtrip ✓
4) timeline event: document_uploaded — بارگذاری سند: آزمایش خون — تست زنده
5) patch: title updated, file untouched ✓
6) invalid mime → 422, nothing stored ✓
7) delete: metadata gone, MinIO object gone, timeline event gone ✓
8) 404s with Persian details: سند یافت نشد.
E2E: ALL CHECKS PASSED
```

## ۵) تصمیم‌های مهندسی مهم

1. **download با ریدایرکت 307 به presigned URL** (نه streaming از بک‌اند) — فایل از خود MinIO سرو می‌شود؛ بک‌اند سبک می‌ماند و اصل فایل از ذخیره‌سازی عبور نمی‌کند. اعتبار: ۱ ساعت.
2. **کلید ذخیره‌سازی یکتا:** `patients/{id}/documents/{uuid}-{نام-پاک‌سازی‌شده}` — uuid از تداخل جلوگیری می‌کند؛ نام فایل sanitize می‌شود (بدون مسیر/نقطه‌های متوالی/فاصله؛ حروف فارسی حفظ می‌شوند). تست همین را شکست داد و اصلاح شد (`..pdf` → `.pdf`).
3. **حذف = سه‌گانه:** آبجکت MinIO ← row فراداده ← رویداد تایم‌لاین (ارجاع چندریختی بدون FK، پس دستی پاک می‌شود). اگر MinIO در دسترس نباشد → 503 و هیچ‌چیز حذف نمی‌شود (no orphan) — به‌عمد قبل از حذف row انجام می‌شود.
4. **آپلود خودش رویداد `document_uploaded` می‌سازد** — تایم‌لاین بدون عملیات دستی معنا داراست و با دادهٔ seed تسک ۲ هم‌خوان است.
5. **`storage_key` در پاسخ API نیست** — کلاینت فقط از `/download` استفاده می‌کند.
6. **استخراج متن (OCR/LLM) عمداً نیست** — طبق معماری پروژه فاز بعدی است؛ سند با `extraction_status=pending` شروع می‌شود.
7. **لایهٔ storage قابل فیک‌شدن** — تست‌های API سریع و مستقل از MinIO ماندند.
8. حداکثر ۲۰MB و whitelist نوع فایل — پیش‌فرض محافظه‌کارانه؛ به‌راحتی در یک ثابت قابل تغییر.

## ۶) هشدارها / رویدادهای محیطی

1. **سرور dev رهاشده (orphan) روی پورت ۸۰۰۰:** یک `uvicorn --reload` (شروع‌شده حدوداً دستی) پورت را می‌گرفت و چون reload داشت کد جدید را سرو می‌کرد؛ باعث bind-error سرور تست و رفتار مبهم شد؛ فرآیندهایش (uvicorn.exe + چند فرزند python) یافته و متوقف شدند. `netstat` ویندوز در این محیط شناسهٔ فرآیند را غلط/خالی نشان می‌داد — `Get-CimInstance` جواب داد. اگر سرور dev خودتان روشن است، بعد از این تسک دوباره `uvicorn app.main:app --reload` را اجرا کنید.
2. **curl ویندوزی Git Bash:** مسیر POSIX در `-F file=@...` کار نمی‌کند (exit 26) — باید مسیر ویندوزی `F:/...` داد؛ E2E نهایی با اسکریپت پایتون (httpx) انجام شد.
3. کنسول ویندوز برای خروجی فارسی به `PYTHONIOENCODING=utf-8` نیاز دارد.
4. `python-multipart` به‌عنوان وابستگی جدید اضافه شد (لازم برای Form/File).
5. پس از E2E اولیه (که سند seed ای را حذف کرد) دیتابیس reseed شد و وضعیت نهایی پاک است؛ در پایان postgres و minio متوقف شدند (volume ها باقی‌اند).

## ۷) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**. پیشنهاد تسک ۷: استخراج متن سند (برای PDFهای متنی و تصاویر با مدل آماده) + نمایش اسناد در فرانت‌اند.
