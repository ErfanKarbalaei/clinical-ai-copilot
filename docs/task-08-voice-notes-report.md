# گزارش تسک ۸ — تبدیل گفتار فارسی به متن (Speechmatics)

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۸ (Task 8) — یادداشت‌های صوتی + STT فارسی با سرویس آمادهٔ Speechmatics
- **تاریخ اجرا:** 2026-08-26
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۱۰۹ تست + E2E با فایل WAV واقعی + SSR)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) معماری STT

```
Upload (multipart) ──► 201 + transcription_status=pending + audio در MinIO ( patients/{id}/voice/… )
        └─(پس از پاسخ)─► BackgroundTask: process_voice_note
                           ├─ status=processing
                           ├─ storage.get_object_bytes (اصل صدا)
                           ├─ stt.transcribe_audio (Speechmatics batch)
                           │    physician_note      → language=fa، بدون diarization
                           │    doctor_patient      → language=fa + diarization=max
                           └─ transcript خام + status=completed/failed
```
- بدون مدل‌سازی/آموزش — سرویس ابری آماده، لایهٔ provider-agnostic نه؛ فقط یک سرویس `stt.py` با کلاینت قابل تزریق (جایگزینی provider بعداً فقط همین فایل).
- رونوشت **خام** نگه داشته می‌شود و هرگز خودکار به تشخیص/یادداشت تبدیل نمی‌شود؛ تبدیل به یادداشت بالینی فقط با بازبینی صریح پزشک (`POST /voice-notes/{id}/note`).

## ۲) جزئیات یکپارچه‌سازی Speechmatics

- **Batch API v2** (`https://asr.api.speechmatics.com/v2`): `POST /jobs` (multipart: config + audio) → poll `GET /jobs/{id}` تا `done` (فاصلهٔ ۳ ثانیه، مهلت ۳۰۰ ثانیه) → `GET /jobs/{id}/transcript?format=json-v2`
- احراز هویت: `Authorization: Bearer $SPEECHMATICS_API_KEY`؛ کلید ۴۰۱/۴۰۳ → پیام «کلید رد شد»
- config: `{"type":"transcription","transcription_config":{"language":"fa","operating_point":"enhanced"[,"diarization":"max"]}}`
- فرمت خروجی json-v2 به متن خوانا تبدیل می‌شود (`format_transcript_json`)؛ نوبت‌های گوینده روی خطوط جدا با برچسب `S1:`/`S2:`
- `SPEECHMATICS_API_KEY` خالی → `SttUnavailableError` → وضعیت failed با دلیل ثبت‌شده در لاگ (رفتار قطعی، بدون کرش)

## ۳) workflowهای پشتیبانی‌شده

| workflow | مسیر | تشخیص گوینده |
| --- | --- | --- |
| یادداشت صوتی پزشک (تک‌نفره) | ضبط/آپلود → متن خام → بازبینی → یادداشت بالینی | ❌ (سریع‌تر/ارزان‌تر) |
| گفتگوی پزشک-بیمار | ضبط/آپلود → متن خام با برچسب گوینده → بازبینی → یادداشت | ✅ diarization=max |

## ۴) endpointها (۸)

`POST /patients/{id}/voice-notes` (multipart؛ 201؛ صوت اصلی در MinIO) · `GET /patients/{id}/voice-notes` (جدیدترین اول) · `GET /voice-notes/{id}` · `GET /voice-notes/{id}/download` (307 presigned) · `PATCH /voice-notes/{id}` (فقط عنوان — متن خام هرگز ویرایش نمی‌شود) · `POST /voice-notes/{id}/transcribe` (202؛ 409 هنگام اجرا) · `POST /voice-notes/{id}/note` (201 — ثبت بازبینی‌شده به‌عنوان یادداشت با `voice_note_id` و source=voice + رویداد تایم‌لاین) · `DELETE /voice-notes/{id}` (204 — صدا+ردیف+رویداد حذف؛ یادداشت‌های مشتق می‌مانند با link=NULL). اعتبارسنجی: WebM/OGG/MP3/M4A/MP4/WAV/FLAC ≤ ۵۰MB؛ پیام‌های 422/404 فارسی.

## ۵) کامپوننت‌های فرانت‌اند

`voice-note-actions.tsx`: دیالوگ ثبت دوحالته — **ضبط با میکروفون مرورگر** (MediaRecorder با انتخاب mime پشتیبانی‌شده + تایمر mm:ss) یا انتخاب فایل؛ عنوان + نوع گفتگو. ردیف‌ها: Badge وضعیت فارسی (در انتظار/در حال تبدیل با pulse/تبدیل انجام شد/ناموفق)، پخش/دانلود صدا، **نمایش رونوشت خام**، **دیالوگ بازبینی→یادداشت** (پیش‌پرشده با متن خام)، تبدیل مجدد، حذف. بخش سروری روی پروندهٔ بیمار + پایش اولین خط رونوشت.

## ۶) تست‌ها — مجموع **۱۰۹ passed** (+۱۷ جدید)

- `test_stt_service.py` (۷): چرخهٔ کامل job با httpx.MockTransport (بدون API واقعی)، درخواست diarization فقط برای گفتگو، اسمبل متن چندگوینده، خطای job، رد کلید، نبود کلید
- `test_voice_notes_api.py` (۱۰): آپلود→تبدیل (تک‌نفره/دوگانه با S1/S2)، رویداد تایم‌لاین، شکست STT→failed، اعتبارسنجی/404، فهرست جدیدترین اول، تغییر عنوان، ریدایرکت دانلود، ثبت یادداشت با پیوند، حذف (صدا+رویداد حذف، یادداشت مشتق باقی با link=NULL)

## ۷) نتیجهٔ تبدیل زندهٔ فارسی

❌ در دسترس نیست — `SPEECHMATICS_API_KEY` تنظیم نشده. مسیر live با کلید واقعی: تنظیم `.env` → `python -m scripts.e2e_voice_notes` → خروجی بخش ۲ همان اسکریپت متن فارسی را چاپ می‌کند. **تأخیر هم اندازه‌گیری نشد** (به کلید و فایل گفتار واقعی وابسته است؛ معماری batch غیرهمزمان است و UI با status badge کار می‌کند).

## ۸) E2E واقعی (بدون کلید) — همه سبز

```
1) upload 201 (WAV واقعی ۳۲KB، عنوان فارسی، duration) | status=pending | lang=fa
2) transcription failed as expected (no key) — دلیل در لاگ
3) اصل صدا بایت‌به‌بایت حفظ شد ✓ (307 → presigned → byte-identical)
4) صدا پس از پردازش همچنان در MinIO + رویداد voice_note_recorded ✓
5) تغییر عنوان ✓   6) تبدیل مجدد 202 → terminal ✓
7) ثبت یادداشت از رونوشت: 201 + پیوند به ضبط ✓
8) حذف: صدا+رویداد پاک، یادداشت مشتق باقی (link=NULL) ✓
```
SSR هم تأیید شد: بخش «یادداشت‌های صوتی» + دکمهٔ میکروفون + Badge «تبدیل ناموفق» روی پروندهٔ بیمار (سرور ۳۰۰۰).

## ۹) قابلیت‌های گویندهٔ «واقعاً پشتیبانی‌شده»

- ✅ تشخیص نوبت‌های گفتگو (دو یا چند گوینده) با برچسب `S1/S2/…` در متن خام — فقط برای نوع doctor_patient درخواست می‌شود
- ❌ نگاشت خودکار «S1=پزشک» / نام‌گذاری گویندگان (الگو خنثی است؛ تشخیص نقش گوینده پیاده نشد — نیاز به منطق بیشتر یا الگوی گفتگو دارد)
- ❌ timestamps کلمه‌به‌کلمه در پاسخ API ذخیره نمی‌شود (فقط متن نامی؛ ستونی برای آن نداریم — بدون تغییر schema طبق اصل تسک)

## ۱۰) هشدارها

1. **بدون کلید، تبدیل‌ها failed می‌شوند** — عمدی و قطعی؛ کلید را در `.env` محلی بگذارید (`.env.example` جای‌نگهدار دارد). تست‌های واحد با MockTransport شکل دقیق درخواست‌ها را قفل کرده‌اند؛ پس از داشتن کلید یک اجرای live توصیه می‌شود.
2. `diarization:"max"` و `operating_point:"enhanced"` بر اساس مستندات v2 تنظیم شده‌اند — در نخستین اجرای live در صورت مغایرت، فقط همین دو خط در `stt.py` اصلاح می‌شود.
3. ضبط مرورگر به کدک وابسته است (Chrome/Firefox: webm/opus؛ Safari: mp4) — پشتیبانی در زمان اجرا تشخیص داده می‌شود؛ حالت «انتخاب فایل» همیشه هست.
4. تبدیل در BackgroundTask صف ندارد — صداهای خیلی طولانی دقایقی طول می‌کشند (batch Speechmatics)؛ برای MVP کافی است.
5. `httpx` به requirements اصلی منتقل شد (قبلاً dev-only بود).
6. فرآیندهای dev قبلی (PyCharm/یادداشت تسک ۷) این بار دست نخوردند؛ سرورها روی ۸۰۰۰/۳۰۰۰ با کد جدید بالا هستند.

## ۱۱) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**. پیشنهاد تسک ۹: صفحهٔ تایم‌لاین بیمار (مصرف `clinical_events`) یا خلاصه‌سازی/پرسش‌وپاسخ با LLM (لایهٔ provider-agnostic).
