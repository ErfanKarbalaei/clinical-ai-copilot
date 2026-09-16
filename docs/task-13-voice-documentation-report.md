# گزارش تسک ۱۳ — مستندسازی صوتی بالینی / لایهٔ STT

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۳ (Task 13) — Clinical Voice Documentation / Speech-to-Text
- **تاریخ اجرا:** 2026-09-17
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۱۹۶ تست + build فرانت‌اند + smoke زندهٔ Speechmatics)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) جریان کار

```
ضبط در مرورگر (MediaRecorder — تسک ۸، بدون تغییر)
      ↓
POST /api/v1/patients/{id}/voice-notes
      ↓ اعتبارسنجی (بیمار/نوع/حجم) → 404 / 422
ذخیرهٔ صدای اصلی در MinIO (دست‌نخورده) + ردیف DB + رویداد timeline
      ↓ پس از پاسخ (background task)
Speechmatics (fa، enhanced؛ diarize برای گفتگوی دو نفره) → transcript خام
      ↓ فقط اگر STT موفق و AI کانفیگ شده باشد
Gemini (AI_PROVIDER/AI_MODEL موجود — پیش‌فرض gemini-3.6-flash)
      ↓ پرامپت قالب‌بندی با قواعد ضد جعل
cleaned_note (دادهٔ مشتق — رونوشت خام همیشه source of truth می‌ماند)
      ↓
Patient Context و Timeline به‌طور خودکار حمل می‌کنند (تسک ۹)
```

این یک **دستیار مستندسازی** است، نه پزشک صوتی — نتیجهٔ پاک‌سازی هرگز به‌تنهایی تشخیص یا نسخه نیست؛ ثبت نهایی همچنان فقط با بازبینی صریح پزشک (تسک ۸: `POST /voice-notes/{id}/note`) انجام می‌شود.

## ۲) انتزاع STT Provider (بدون بازنویسی workflow)

`services/stt.py` بازسازماندهی شد (منطق Speechmatics **خط‌به‌خط همان قبل** است):

- `SpeechToTextProvider` (Protocol کوچک): فقط یک متد `transcribe(...)`
- `SpeechmaticsProvider`: پیاده‌سازی فعلی — batch API، زبان `fa`، operating point `enhanced`، diarization `max` فقط برای گفتگوی پزشک–بیمار
- `get_stt_provider()`: انتخاب بر اساس `STT_PROVIDER`؛ کلید از `STT_API_KEY` با fallback به `SPEECHMATICS_API_KEY` (سازگار با تسک ۸ — .env فعلی بدون تغییر کار می‌کند)؛ نام ناشناخته → `TranscriptionError`
- `transcribe_audio()`: facade با همان امضای قبل — pipeline صوت تغییری در فراخوانی نداشت

افزودن Deepgram یا هر provider دیگر در آینده = یک کلاس + یک branch در factory؛ بدون دست زدن به voice-note workflow.

## ۳) پاک‌سازی هوشمند transcript — پرامپت امن

سرویس جدید `services/voice_note_cleanup.py`:

- `attempt_cleanup(db, voice_note)`: **best-effort و هرگز exception بیرون نمی‌دهد** — پس از commit شدن موفق transcription فراخوانی می‌شود
- بدون کلید AI (`AIUnavailableError`) → بی‌صدا رد می‌شود (`cleanup_status=pending`)
- سقف دفاعی ۲۰هزار کاراکتر transcript (الگوی تسک ۱۲)
- پرامپت، قواعد الزامی تسک را دارد: فقط اطلاعات موجود در رونوشت؛ ممنوعیت افزودن تشخیص/دارو/علامت/اندازه‌گیری؛ ممنوعیت استنتاج؛ حفظ عدم‌قطعیت («اگر مبهم است، مبهم بماند»); «FORMATTING AND CLARIFICATION ONLY — never clinical reasoning»؛ سکشن فقط با پشتوانهٔ رونوشت؛ حداکثر ~۲۰۰ واژه فارسی؛ حفظ برچسب گوینده‌ها (S1/S2)
- از لایهٔ AI موجود (تسک ۱۰/۱۰.۵) استفاده می‌کند — **هیچ کانفیگ جدیدی لازم نیست**؛ همان `AI_PROVIDER=gemini` و `AI_MODEL` (پیش‌فرض `gemini-3.6-flash`)

## ۴) معناشنسی خطا (مهم‌ترین طراحی)

| اتفاق | transcription_status | transcript | cleaned_note | cleanup_status | error_message |
|---|---|---|---|---|---|
| Speechmatics خطا | `failed` | null | null | `pending` | متن خطا (ذخیره می‌شود) |
| STT ✅ + Gemini ✅ | `completed` | حفظ | ذخیره | `completed` | null |
| STT ✅ + Gemini خطا | `completed` **می‌ماند** | **سالم** | null | `failed` | null |
| AI کانفیج نشده | `completed` | حفظ | null | `pending` | null |

- صدای اصلی (MinIO) و رونوشت خام **هرگز** به‌خاطر خطای Gemini از بین نمی‌روند
- تبدیل مجدد (`POST /voice-notes/{id}/transcribe`) → `cleaned_note` قبلی discard می‌شود (ناسازگاری با رونوشت جدید ناممکن)
- `processed_at`: timestamp پایان پردازش (موفق یا ناموفق)

## ۵) Migration

`fe6bf890d790` (بعد از `b309d1be6900`): افزودن `voice_notes.cleanup_status` (enum بومی PG با server_default='pending' — مطابق درس تسک ۱۲، enum صریحاً در upgrade ساخته و در downgrade حذف می‌شود)، `cleaned_note`، `error_message`، `processed_at` (timestamptz). چرخهٔ upgrade→downgrade→upgrade + `alembic check` سبز؛ ستون‌ها با information_schema تأیید شد.

## ۶) API

بدون endpoint جدید — جریان همان `POST /patients/{id}/voice-notes` تسک ۸ است (زبان از `STT_LANGUAGE`). `VoiceNoteResponse` حالا شامل `cleanup_status`، `cleaned_note`، `error_message`، `processed_at` است و در همهٔ GET/LIST و Patient Context برمی‌گردد.

## ۷) فرانت‌اند (فارسی RTL، هماهنگ با طراحی موجود)

- `ViewCleanedNoteButton` (آیکون ✨): دیالوگ فقط-خواندنی یادداشت پاک‌سازی‌شده + سلب مسئولیت («رونوشت خام و فایل صوتی معتبرترین منبع هستند»)
- Badge «پاک‌سازی شد» فقط وقتی cleanup_status=completed
- متن خطا (`error_message`) در سطر یادداشت وقتی تبدیل ناموفق است
- دیالوگ بازبینی→یادداشت بالینی: نقطهٔ شروع = نسخهٔ پاک‌سازی‌شده (در صورت وجود) + دکمهٔ یک‌کلیکی «نسخهٔ پاک‌سازی‌شده» برای بازگرداندن آن — تصمیم نهایی همچنان با پزشک
- دکمهٔ ضبط/توقف/طول ضبط/MediaRecorder و بقیهٔ UI صوت از تسک ۸ دست‌نخورده

## ۸) تست‌ها — مجموع **۱۹۶ passed** (قبلی: ۱۸۳، جدید: +۱۳)

**`tests/test_voice_note_cleanup.py` (۹):** قواعد ایمنی پرامپت · ساخت پیام با سقف · STT→cleanup موفق (پرامپت grounded) · شکست Gemini با حفظ کامل transcript و completed ماندن status · skip بدون AI · شکست STT (error_message + processed_at + بدون فراخوانی AI) · retry و discard پاک‌سازی قبلی · حمل در Patient Context و Timeline · رد فایل بیش از حد بزرگ.

**`tests/test_stt_service.py` (+۴):** dispatch و fallback کلید · provider ناشناخته · نبود کلید · delegate شدن `transcribe_audio` به provider.

**`tests/test_voice_notes_api.py`:** fixture موجود deterministic شد (AI همیشه off در این تست‌ها تا نتیجه به .env توسعه‌دهنده وابسته نباشد) — همهٔ ۱۰ تست قبلی بدون تغییر منطق سبز ماندند.

همهٔ فراخوانی‌های STT و LLM در تست‌ها mock هستند. تسک‌های ۱۰ (chat)، ۱۱ (ایمنی دارو) و ۱۲ (تحلیل اسناد) با اجرای کل suite راستی‌آزمایی شدند (تست‌های موجودشان پاس).

`tsc --noEmit` و `next build` فرانت‌اند بدون خطا.

## ۸.۵) Smoke زنده (backend روی :8003، اسکریپت `scripts/smoke_task13_voice_cleanup.py`)

```
1) patient created: id=4
2) uploaded 32044 bytes → voice_note=4 (transcription=pending, cleanup=pending)
3) transcription terminal: completed        ← جاب REAL Speechmatics از طریق کلاس Provider جدید
   transcript=None                          ← انتظار: WAV تُن است، گفتار واقعی نیست
4) cleanup_status=pending cleaned_note=None ← درست: رونوشت خالی → پاک‌سازی skip
   processed_at=2026-09-16T22:50:29Z ✓
5) patient context carries the voice note ✓
6) original audio preserved: True (32044 bytes — byte-identical) ✓
7) cleanup ✓ (حذف یادداشت صوتی + بیمار تست)
```

جریان واقعی Speechmatics + معناشنسی skip روی رونوشت خالی + حفظ بایت‌به‌بایت صدا به‌صورت زنده راستی‌آزمایی شد. مرحلهٔ Gemini روی این ماشین زنده نشد (شبکهٔ Google بلاک؛ بدون گفتار واقعی هم بی‌معنا بود) — صادقانه گزارش می‌شود، جعل نشد.

## ۹) محدودیت‌ها

1. **پاسخ واقعی LLM روی این ماشین تست نشد** — شبکهٔ Google بلاک است (تشخیص تسک ۱۲)؛ برای تست زنده `AI_PROXY` لازم است. منطق پاک‌سازی با provider فرقی کاملاً تست شد.
2. Smoke زنده با WAV تُن (بدون گفتار) انجام شد — transcript فارسی واقعی نیازمند فایل گفتار واقعی است (سرویس Speechmatics در تسک ۸ با فایل واقعی سبز شده بود).
3. cleanup همگام در همان background task است؛ مدل کند + رونوشت طولانی → کل پردازش طولانی‌تر می‌شود (تنظیم `AI_TIMEOUT_SECONDS`).
4. سابقهٔ پاک‌سازی نگه داشته نمی‌شود (آخرین نسخه override می‌شود) — برای MVP کافی.

## ۱۰) فایل‌ها

**ساخته‌شده:** `services/voice_note_cleanup.py` · `alembic/versions/fe6bf890d790_*.py` · `tests/test_voice_note_cleanup.py` · `scripts/smoke_task13_voice_cleanup.py` · گزارش
**تغییریافته:** `core/config.py` (+۳ متغیر STT) · `services/stt.py` (انتزاع provider) · `services/voice_notes.py` (chain + error tracking) · `api/v1/routes/voice_notes.py` (STT_LANGUAGE + توضیح) · `models/voice_note.py` (+۴ ستون) · `schemas/voice_note.py` (+۴ فیلد) · `tests/test_stt_service.py` (+۴) · `tests/test_voice_notes_api.py` (fixture) · `frontend/src/lib/types.ts` · `frontend/src/lib/format.ts` · `frontend/src/components/patients/voice-note-actions.tsx` · `frontend/src/app/patients/[id]/page.tsx` · `.env.example` · READMEها
