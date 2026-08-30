# گزارش تسک ۱۰.۵ — اتصال لایهٔ هوش مصنوعی به Gemini

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۰.۵ (Task 10.5) — اتصال provider-agnostic موجود به Google Gemini (بدون بازطراحی)
- **تاریخ اجرا:** 2026-08-31
- **وضعیت:** ✅ تکمیل‌شده — تست سیم واقعی با گوگل انجام شد؛ فقط کلید معتبر برای پاسخ واقعی لازم است
- **کامیت:** هنوز کامیت نشده است

---

## ۱) رویکرد

**افزودن، نه بازنویسی.** کلاس جدید `GeminiProvider` در همان `services/ai.py` رابطِ `LLMProvider` تسک ۱۰ را پیاده می‌کند و `get_provider()` بر اساس تنظیم `AI_PROVIDER` dispatch می‌کند — endpoint چت، اسکیما، فرانت‌اند و تست‌های قبلی **هیچ تغییری نکردند**.

## ۲) جزئیات GeminiProvider

- **API بومی:** `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` با هدر `x-goog-api-key`
- نگاشت نقش‌ها: `system` → `system_instruction` · `assistant` → نقش `model` (اصطلاح Gemini) · `user` → `user`
- پاسخ: الحاق همهٔ `candidates[0].content.parts[*].text` (چند-پارتی)
- خطاها: ۴۰۱/۴۰۳ و ۴۰۰ِ حاوی «API key not valid» → «کلید رد شد»؛ ۴۲۹ → «سهمیه»؛ سایر → کد + ۲۰۰ کاراکتر پیام؛ همه → 502 فارسی در API
- بدون SDK — همان httpx موجود

## ۳) مدل انتخاب‌شده

**`gemini-2.5-flash`** (پیش‌فرض وقتی `AI_MODEL` خالی باشد) — سریع/ارزان، پشتیبانی چندزبانهٔ قوی (فارسی)، پنجرهٔ متنی بزرگ (مناسب context کامل بیمار)؛ مناسب پرسش‌وپاسخ بالینی grounded. با `AI_MODEL` در `.env` قابل‌تغییر (مثلاً `gemini-2.5-pro`).

## ۴) متغیرهای محیطی دقیق

در `F:\clinical-ai-copilot\.env` (ریشهٔ مخزن — همان فایل `SPEECHMATICS_API_KEY`؛ پس از تغییر، ری‌استارت uvicorn):

```
AI_PROVIDER=gemini          # ← فعلاً ست شده است
AI_API_KEY=<کلید-معتبر-Google-AI-Studio>   # ← فقط این مانده است
# اختیاری:
AI_MODEL=                   # خالی = gemini-2.5-flash
```

- بدون کلید: چت به‌صورت قطعی 503 می‌دهد («سرویس هوش مصنوعی تنظیم نشده است»)
- بازگشت به OpenAI-compatible: `AI_PROVIDER=openai_compatible` (+ `AI_API_KEY`/`AI_BASE_URL` مربوطه)

## ۵) آیا درخواست واقعی API موفق بود؟

**تست سیم واقعی ✅ / پاسخ واقعی LLM — هنوز نه (کلید معتبر نیست).**

```
تنظیم موقت AI_API_KEY=INVALID-KEY-FOR-WIRE-TEST + AI_PROVIDER=gemini:
POST /api/v1/patients/8/chat → HTTP 502 (پاسخ نداد) — زمان: 1.25s (رفت‌وبرگشت واقعی شبکه)
confirm مستقیم همان درخواست به گوگل با curl → HTTP 403 (Google جواب داد = URL/header/body درست)
در نتیجه: dispatch → GeminiProvider → endpoint واقعی گوگل → نگاشت خطای کلید، همه درست کار می‌کند؛
فقط کلید معتبر برای پاسخ واقعی مدل لازم است (پس از افزودن، همان POST جواب فارسی می‌دهد).
```

## ۶) نمونهٔ وضعیت پاسخ

| سناریو | کد | بدنه |
|---|---|---|
| کلید خالی | 503 | `{"detail":"سرویس هوش مصنوعی تنظیم نشده است (AI_API_KEY)."}` |
| کلید نامعتبر (واقعی، تست‌شده) | 502 | `{"detail":"سرویس هوش مصنوعی پاسخ نداد؛ کمی بعد دوباره تلاش کنید."}` |
| کلید معتبر | 200 | `{"patient_id":8,"question":"…","answer":"… (فارسی، grounded)","generated_at":"…"}` |

## ۷) تست‌ها — مجموع **132 passed** (+۵)

فرمت wire بومی (URL، هدر x-goog-api-key، system_instruction، نگاشت assistant→model در contents)، الحاپ پارت‌ها، نگاشت «API key not valid» و 429، dispatch روی `AI_PROVIDER` با مدل پیش‌فرض هر provider (`gemini-2.5-flash` / `gpt-4o-mini`)، و کل suite قبلی سبز (route/فرانت‌اند تسک ۱۰ دست‌نخورده).

## ۸) فایل‌های تغییریافته

- `backend/app/services/ai.py` (+GeminiProvider، dispatch، ثابت‌های مدل پیش‌فرض) — تنها فایل کد بک‌اندِ منطقی
- `backend/app/core/config.py` (+`AI_PROVIDER`؛ `AI_MODEL` پیش‌فرض خالی = پیش‌فرض provider)
- `backend/tests/test_chat_api.py` (+۵ تست)
- `.env.example` (بخش AI بازنویسی؛ default `AI_PROVIDER=gemini`) · `.env` محلی (`AI_PROVIDER=gemini` ست شد)
- READMEهای ریشه/بک‌اند + گزارش

## ۹) محدودیت‌های باقی‌مانده

1. **کلید معتبر Gemini هنوز تنظیم نشده** — تنها قدم باقی‌مانده؛ همه‌چیز آماده است
2. `finishReason` های Gemini (مانند SAFETY/RECITATION) به‌صورت خاص هندل نشده‌اند — به‌عنوان پاسخ خالی/خطای عمومی ظاهر می‌شوند
3. بدون streaming (پاسخ یک‌جا)؛ پنجرهٔ context مدل محدود به سهم prompt است (فعلاً برش ۲۰۰۰ کاراکتری تسک ۱۰ کفایت می‌کند)
4. هزینه/تأخیر وابسته به Google؛ fallback خودکار بین providerها پیاده نشده (تعویض دستی با env)

## ۱۰) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**.
