# گزارش تسک ۱۲ — تحلیل هوش مصنوعی اسناد بالینی

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۲ (Task 12) — تحلیل AI متن استخراج‌شدهٔ سند + ذخیرهٔ خلاصهٔ مشتق
- **تاریخ اجرا:** 2026-09-16
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۱۸۳ تست + smoke زنده)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) معماری (بدون بازطراحی — بازاستفادهٔ کامل)

```
Upload (تسک ۶) → MinIO (اصل فایل، دست‌نخورده)
      ↓ پس از پاسخ
استخراج قطعی متن (تسک ۷: pypdf/OCR) → extracted_text
      ↓ فراخوانی صریح پزشک
POST /documents/{id}/analyze
      ↓
provider موجود (تسک ۱۰/۱۰.۵: Gemini) + پرامپت امن خلاصه‌سازی
      ↓
ai_summary + analysis_status (دادهٔ مشتق — هرگز جایگزین اصل/extracted_text نمی‌شود)
```

- سرویس جدید `services/document_analysis.py`: `analyze_document` همگام (یک فراخوانی provider — بدون صف/worker) + پرامپت با قواعد ایمنی (فقط متن واقعی، ساختار «یافته‌های کلیدی/نکات قابل توجه/محدودیت»، فارسی، سقف ~۲۰۰ واژه) + سقف دفاعی ۲۰هزار کاراکتر متن
- خطاها مطابق الگوی chat: 503 بدون کلید، 502 خطای provider (با لاگ علت واقعی)، 409 اگر استخراج completed نباشد — پیام‌های فارسی
- شکست تحلیل → `analysis_status=failed` ذخیره می‌شود ولی اصل فایل و extracted_text دست‌نخورده می‌مانند (تست‌شده)
- **Patient Context (تسک ۹) به‌طور خودکار** خلاصه را حمل می‌کند (همان DocumentResponse) — بدون تغییر در آن سرویس

## ۲) Migration

`b309d1be6900` — افزودن `documents.analysis_status` (enum بومی PG با server_default='pending') و `documents.ai_summary` (text nullable). اصلاحات دستی روی autogenerate: (الف) ایجاد صریح enum در upgrade (باگ شناخته‌شدهٔ Alembic: `op.add_column` با enum درون‌خطی نوع را نمی‌سازد → خطای UndefinedObject)، (ب) drop صریح enum در downgrade. چرخهٔ upgrade→downgrade→upgrade + `alembic check` سبز؛ ردیف‌های قبلی با پیش‌فرض pending پر شدند (تست raw-SQL).

## ۳) API

`POST /api/v1/documents/{document_id}/analyze` → `DocumentResponse` با `ai_summary`/`analysis_status` جدید (در GET/LIST هم برمی‌گردند). 404/409/502/503 فارسی. بدون endpoint حذف/ویرایش خلاصه — تحلیل مجدد همان سند خلاصه را بازنویسی می‌کند.

## ۴) تست‌ها — مجموع **183 passed** (قبلی: 172، جدید: +11)

پرامپت grounded + سقف متن · قواعد ایمنی پرامپت · تحلیل موفق (خلاصه ذخیره، متن اصلی سالم) · 409 بدون استخراج/متن خالی · بازنویسی مجدد · 502 (failed ذخیده + منبع حقیقت سالم) · 503 · 404 · فیلدهای جدید در list/get · حضور در Patient Context · پیش‌فرض server (raw insert).

## ۵) Smoke زنده (upload واقعی، سرویس :8003)

```
1) upload 201 | extraction: pending | analysis: pending
2) استخراج قطعی → completed | "HbA1c" در متن ✓
3) analyze قبل از استخراج (سند OCR-ناپذیر) → 409 فارسی ✓
4) analyze با provider واقعی → 502 (بلاک شبکهٔ Gemini — محدودیت محیط)
   | analysis_status=failed ذخیره شد | extracted_text سالم ✓
5) cleanup ✓
```

## ۶) محدودیت‌ها

1. **پاسخ واقعی LLM روی این ماشین قابل‌تست نبود** — شبکه به Google بلاک است (403 HTML لبه، diagnostic تسک قبل)؛ با `AI_PROXY` فعال خواهد شد. منطق با provider فرضی کاملاً تست شده.
2. تحلیل همگام است؛ سندهای خیلی بزرگ + مدل کند → timeout بالای 60s ممکن (تنظیم AI_TIMEOUT_SECONDS)
3. بدون دکمهٔ «تحلیل» در UI (خارج از محدودهٔ این تسک — frontend فقط type-sync شد)
4. سابقهٔ تحلیل نگه داشته نمی‌شود (آخرین خلاصه override می‌شود) — برای MVP کافی

## ۷) فایل‌ها

**ساخته‌شده:** `services/document_analysis.py` · `alembic/versions/b309d1be6900_*.py` · `tests/test_document_analysis_api.py` · `scripts/smoke_document_analysis.py` · گزارش
**تغییریافته:** `models/enums.py` (+AnalysisStatus) · `models/document.py` (+۲ ستون) · `schemas/document.py` (+۲ فیلد) · `routes/documents.py` (+endpoint، +import logging) · `frontend/src/lib/types.ts` (همگام‌سازی type — بدون UI) · READMEها
