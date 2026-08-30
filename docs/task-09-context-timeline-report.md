# گزارش تسک ۹ — زمینهٔ بیمار و تایم‌لاین بالینی

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۹ (Task 9) — Patient Context Builder + Clinical Timeline (بدون LLM/RAG)
- **تاریخ اجرا:** 2026-08-30
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۱۱۸ تست + تأیید زندهٔ SSR)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) معماری

**Patient Context Builder** (`services/patient_context.py`): یک کوئری زنده از همهٔ جدول‌های موجود — بدون هوش مصنوعی، بدون جدول/کپی جدید (دادهٔ مشتق هرگز از منبع حقیقت جدا نمی‌شود). خروجی همان schemaهای پاسخِ موجود را بازاستفاده می‌کند → ورودی آمادهٔ «AI Copilot» آینده.

**Clinical Timeline**: به‌جای اتکا به جدول `clinical_events` (که فقط بخشی از رکوردها را پوشش می‌دهد — مثلاً آزمایش‌ها را ندارد)، تایم‌لاین از خود رکوردها مشتق می‌شود: اسناد، آزمایش‌ها، یادداشت‌ها، یادداشت‌های صوتی، شروع/رفع بیماری‌ها و شروع/پایان داروها. همان واژگان `event_type`/`source_type` جدول رویدادها استفاده می‌شود (`document_uploaded` ، `lab_result` ، `note_created` ، `voice_note_recorded` ، `condition_onset/resolved` ، `medication_started/stopped`).

## ۲) APIها (۲ endpoint جدید)

| متد | مسیر | توضیح |
| --- | --- | --- |
| GET | `/api/v1/patients/{id}/context` | همهٔ داده‌های بیمار در یک پاسخ: `{patient, conditions, medications(کامل با وضعیت), allergies, lab_results, documents(با متن استخراجی), voice_notes(با رونوشت خام), clinical_notes, generated_at}` — 404 اگر بیمار نباشد |
| GET | `/api/v1/patients/{id}/timeline` | `{items, total}` — جدیدترین اول؛ هر آیتم `{event_type, date, title, description, source_type, source_id}` |

- تاریخِ مفقود → fallback به `created_at` همان رکورد (هیچ رویدادی حذف نمی‌شود)؛ تاریخ‌ها همگی timezone-aware نرمال می‌شوند (تاریخ خالص → نیمه‌شب UTC)
- مرتب‌سازی قطعی: `(date desc, source_type, source_id)`
- سقف دفاعی ۲۰۰ آیتم در هر بخش context
- endpointهای قبلی (از جمله `/overview`) دست‌نخورده و سالم

## ۳) فرانت‌اند

- صفحهٔ بیمار حالا **لایهٔ Context را مستقیم مصرف می‌کند** (یک fetch به‌جای سه fetch موازی) — داروهای فعال با فیلتر روی status، آزمایش/یادداشت‌ها با slice(0,5)، بقیهٔ بخش‌ها بدون تغییر
- کارت تمام‌عرض **«تایم‌لاین بالینی»** بعد از پروفایل: خط عمودی RTL (کلاس‌های منطقی `border-s/ps-`)، دات + آیکون مخصوص هر نوع رویداد، عنوان/توضیح فارسی، تاریخ جلالی
- حالت خالی/خطا با کامپوننت‌های موجود EmptyState/ErrorState — طراحی RTL فارسی و بقیهٔ صفحه دست‌نخورده

## ۴) تست‌ها — مجموع **۱۱۸ passed** (+۹ جدید)

بخش‌های context با دادهٔ کامل (شامل extracted_text و رونوشت صوتی) · تاریخچهٔ دارویی در context (active اول، stopped می‌ماند) · بیمار خالی (همهٔ بخش‌ها `[]`) · 404ها · مرتب‌سازی زمانی با تاریخ‌های کنترل‌شده (سند→دارو→آزمایش→بیماری) · fallback تاریخ مفقود · رویدادهای رفع/قطع · ارجاع source درست · تایم‌لاین خالی · کل suite قبلی (سالم‌بودن APIهای موجود).

## ۵) تأیید زنده (خروجی واقعی)

```
context: sections {conditions:2, medications:2, allergies:1, lab_results:3,
                  documents:3, voice_notes:4, clinical_notes:2}
         meds: [(Metformin 500, active), (Losartan 50, active)]
timeline: total=16 | sorted desc: True
          2026-08-30 voice_note_recorded «یادداشت صوتی: …» … 2026-08-26 document_uploaded «سند: …»
404 context/timeline ✓ | overview همچنان 200 ✓
SSR: «تایم‌لاین بالینی» + «۱۶ رویداد — جدیدترین اول» + آیکون‌ها، RTL سالم
```

## ۶) فایل‌ها

**ساخته‌شده:** `services/patient_context.py` · `schemas/patient_context.py` · `tests/test_patient_context_api.py` · گزارش
**تغییریافته:** `routes/patients.py` (+۲ endpoint) · فرانت‌اند: `types.ts`/`api.ts`/`page.tsx` (رفکتور به context + کارت تایم‌لاین) · READMEها — **بدون تغییر مدل/مایگریشن/Speechmatics/قابلیت‌های دیگر**

## ۷) محدودیت‌های باقی‌مانده

1. Context حجم محدودی ندارد (سقف ۲۰۰ در هر بخش) — برای بیماران با سابقهٔ خیلی طولانی بعداً صفحه‌بندی/خلاصه‌سازی داده‌محور لازم می‌شود
2. تایم‌لاین از رکوردها مشتق می‌شود؛ جدول `clinical_events` همچنان برای رویدادهای دستی/آینده باقی است ولی فعلاً در تایم‌لاین ادغام نشده (دو منبع ممکن است هم‌پوشانی داشته باشند اگر هر دو مصرف شوند — فعلاً فقط مشتق استفاده می‌شود)
3. عنوان‌های تایم‌لاین فارسی‌اند (مناسب UI)؛ برای پرامپت AI آینده شاید نسخهٔ English-key هم لازم شود — تصمیم فاز AI

## ۸) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**. پیشنهاد تسک ۱۰: دستیار هوش مصنوعی بالینی (چت/پرسش‌وپاسخ) با مصرف همین Context — لایهٔ provider-agnostic.
