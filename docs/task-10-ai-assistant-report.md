# گزارش تسک ۱۰ — دستیار هوشمند بالینی (Clinical Chat)

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۰ (Task 10) — چت/پرسش‌وپاسخ بالینی مبتنی بر Context بیمار (بدون RAG)
- **تاریخ اجرا:** 2026-08-31
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۱۲۷ تست + تأیید زندهٔ API و SSR)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) پیاده‌سازی Provider

`backend/app/services/ai.py` — **provider-agnostic** با کمترین پیچیدگی:
- یک پیاده‌سازی: کلاینت **OpenAI-compatible** `POST {AI_BASE_URL}/chat/completions` با httpx (بدون SDK، بدون وابستگی جدید)
- تعویض provider فقط با env: OpenAI / OpenRouter / Ollama / vLLM / LM Studio (`AI_BASE_URL=http://localhost:11434/v1`)
- `LLMProvider` (Protocol) + `get_provider()` کش‌شده — جایگزینی provider = پیاده‌سازی یک متد `complete`
- خطاها: بدون کلید → `AIUnavailableError` → **503**؛ خطای شبکه/کلید/سهمیه → `AIError` → **502** (پیام فارسی)
- **System prompt** قواعد ایمنی: پاسخ فقط مبتنی بر دادهٔ پرونده، منع ساخت اطلاعات، تصریح نهایی‌بودن تصمیم با پزشک، پاسخ فارسی با حفظ نام‌های لاتین دارو/آزمایش
- `build_user_message`: Context بیمار (تسک ۹) به JSON سریال و فیلدهای متنی بلند (extracted_text/transcript/content) به ۲۰۰۰ کاراکتر بریده می‌شوند

## ۲) API

`POST /api/v1/patients/{patient_id}/chat`
- ورودی: `{question: str(1..2000), history?: [{role: user|assistant, content}]≤20}` — history به ۶ نوبت آخر سمت سرور محدود می‌شود
- خروجی: `{patient_id, question, answer, generated_at}`
- بدون ذخیره‌سازی (Stateless) — هیچ جدول/مایگریشن جدیدی اضافه نشد؛ تاریخچهٔ نمایشی فقط سمت کلاینت
- 404 بیمار ناموجود / 422 اعتبارسنجی / 503 تنظیم‌نشده / 502 خطای provider

## ۳) فرانت‌اند

`components/patients/clinical-chat.tsx` (client) در انتهای صفحهٔ بیمار، با طراحی موجود:
- کادر پرسش (Textarea) + دکمهٔ «ارسال» (آیکون Send با فلیپ RTL)
- **حالت بارگذاری** («در حال بررسی پرونده و پردازش پاسخ…» + اسپینر، دکمه غیرفعال)
- حباب‌های گفتگو RTL (پرسش کاربر متمایز، پاسخ full-width با whitespace-pre-wrap) + اسکرول خودکار
- تاریخچهٔ پرسش‌های قبل (۶ نوبت) برای سؤالات پیگیری — state کلاینت
- پیام خطای فارسی (ApiError) + **سلب مسئولیت پزشکی** ثابت زیر فرم
- حالت خالی با نمونه‌پرسش فارسی؛ بدون بازطراحی صفحه (همهٔ بخش‌های قبلی سالم)

## ۴) تست‌ها — مجموع **۱۲۷ passed** (+۹)

- Provider با MockTransport: شکل دقیق درخواست (URL، Bearer، model، ترتیب messages، history)، نگاشت خطای ۴۰۱، بدون‌کلید → Unavailable
- `build_user_message`: grounded بودن + برش فیلدهای بلند
- API: پاسخ ۲۰۰ با answer (فیک provider)، وجود دادهٔ بیمار در پرامپت (grounding)، سقف history، 503 بدون کلید، 502 خطای provider، 422 (سؤال خالی/نقش نامعتبر)، 404
- کل suite قبلی: سبز (APIهای موجود دست‌نخورده)

## ۵) تأیید زنده

```
POST /patients/8/chat {"question":"خلاصه وضعیت بیمار چیست؟"}
  → 503 {"detail":"سرویس هوش مصنوعی تنظیم نشده است (AI_API_KEY)."}   ← بدون کلید، قطعی
empty question → 422 | missing patient → 404 | bad history role → 422
openapi: ['/api/v1/patients/{patient_id}/chat'] ✓
SSR (:3000): «دستیار هوشمند بالینی» + placeholder + «ارسال» + سلب مسئولیت، RTL سالم، بقیهٔ صفحه سالم
```
پاسخ واقعی LLM نیاز به `AI_API_KEY` دارد (زیر §۶) — منطق provider با mock قفل شده است.

## ۶) متغیرهای محیطی لازم

| متغیر | الزامی | پیش‌فرض | توضیح |
| --- | --- | --- | --- |
| `AI_API_KEY` | برای پاسخ واقعی ✅ | (خالی) | کلید provider — خالی = 503 قطعی |
| `AI_BASE_URL` | ❌ | `https://api.openai.com/v1` | هر endpoint سازگار با OpenAI (مثلاً Ollama) |
| `AI_MODEL` | ❌ | `gpt-4o-mini` | نام مدل |

در `.env.example` جای‌نگهدار اضافه شد (بدون هیچ مقدار واقعی).

## ۷) فایل‌ها

**ساخته‌شده:** `services/ai.py` · `schemas/chat.py` · `routes/chat.py` · `tests/test_chat_api.py` · `components/patients/clinical-chat.tsx` · گزارش
**تغییریافته:** `config.py` (۵ تنظیم AI_*) · `api.py` · `.env.example` · فرانت‌اند `types.ts`/`api.ts`/`page.tsx` · READMEها — **بدون تغییر مدل/مایگریشن/Speechmatics/بخش‌های دیگر**

## ۸) محدودیت‌ها

1. بدون کلید، چت 503 می‌دهد (رفتار قطعی و تست‌شده) — تنظیم `.env` + ری‌استارت uvicorn
2. گفتگو ذخیره نمی‌شود (رفرش = پاک شدن نمایش) — تصمیم آگاهانه برای MVP بدون مایگریشن
3. بدون citation/منبع شواهد پزشکی (PubMed/…) — فاز «evidence» طبق نقشهٔ پروژه
4. ارسال کامل context در هر درخواست — برای پرونده‌های بسیار بزرگ بعداً برش هوشمند لازم می‌شود (فعلاً سقف ۲۰۰/بخش + برش ۲۰۰۰ کاراکتری متن‌ها)
5. Persian-only answers طبق دستور سیستم؛ مدل‌های ضعیف ممکن است قواعد grounding را نقض کنند — پایش پاسخ‌ها بر عهدهٔ پزشک

## ۹) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**.
