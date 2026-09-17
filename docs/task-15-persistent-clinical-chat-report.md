# گزارش تسک ۱۵ — گفتگوی بالینی ماندگار

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۵ (Task 15) — Persistent Clinical Chat
- **تاریخ اجرا:** 2026-09-17
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۲۲۹ تست + build فرانت‌اند + smoke زنده)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) معماری (بازاستفادهٔ کامل — بدون بازطراحی)

```
انتخاب/ساخت گفتگو → POST /conversations/{id}/messages
      ↓
۱. پیام پزشک اول persist می‌شود (اگر AI شکست بخورد، رد قابل‌ردیابی می‌ماند)
۲. Context بیمار همان لحظه از تسک ۹ ساخته می‌شود (هرگز snapshot نمی‌شود)
   + ۲۰ پیام آخر گفتگو به‌عنوان history (مفهوماً جدا از Context)
   + پیام جاری به‌صورت جدا
      ↓
همان provider موجود (تسک ۱۰/۱۰.۵) — medication_safety=true فقط پرامپت را به نسخهٔ تسک ۱۴ عوض می‌کند
      ↓
۳. پاسخ دستیار persist می‌شود + updated_at گفتگو به‌روز می‌شود
```

- endpoint بدون-state تسک ۱۰ (`POST /patients/{id}/chat`) **دست‌نخورده باقی ماند** (سازگاری) — endpointهای گفتگوی ماندگار در کنارش اضافه شدند.
- `ai.py`، `patient_context.py`، تسک ۱۴ (`ai_medication_safety.py`) — صفر تغییر، فقط import.

## ۲) دیتابیس + Migration

جدول `conversations` (id, patient_id→FK CASCADE+index, title با پیش‌فرض «گفتگوی جدید», created_at/updated_at) و `conversation_messages` (id, conversation_id→FK CASCADE+index, role enum بومی `chat_role` = user|assistant, content Text NOT NULL, timestamps). enum جدید `ChatRole` در `enums.py`. Migration `03378aed5376` (بعد از fe6bf890d790) — چرخهٔ upgrade→downgrade→upgrade سبز + `alembic check` پاک.

> نکتهٔ مهندسی جدید مستندشده در خود migration: برخلاف `add_column`، `create_table` خودش enum بومی را می‌سازد — create صریح + create_table باعث DuplicateObject می‌شود؛ explicit create حذف شد، drop صریح در downgrade ماند.

حذف گفتگو → پیام‌ها cascade حذف می‌شوند (تست‌شده). حذف بیمار → گفتگوها cascade.

## ۳) API (۵)

| متد | مسیر | رفتار |
|---|---|---|
| POST | `/patients/{id}/conversations` | 201؛ title اختیاری، پیش‌فرض «گفتگوی جدید» |
| GET | `/patients/{id}/conversations` | جدیدترین updated_at اول |
| GET | `/conversations/{id}` | metadata + پیام‌ها (کهن‌ترین اول) |
| POST | `/conversations/{id}/messages` | تبادل ماندگار (بالا) → `{user_message, assistant_message}` |
| DELETE | `/conversations/{id}` | 204 + cascade پیام‌ها |

خطاها: 404 گفتگو/بیمار فارسی · 422 پیام خالی/بلند · 503 بدون کلید · 502 خطای provider با پیام «پیام شما ثبت شد و می‌توانید دوباره تلاش کنید» — **پاسخ دستیار هرگز جعل نمی‌شود** (پیام کارکبر می‌ماند، ردیف assistant ساخته نمی‌شود).

History: سقف ۲۰ پیام اخیر (ثابت ماژول؛ پیام جاری جداگانه ارسال می‌شود). عنوان: اگر پیش‌فرض باشد و اولین پیام باشد → عنوان قطعیِ ۵۰ کاراکتری از خود پیام (بدون LLM)؛ عنوان دستی هرگز بازنویسی نمی‌شود.

## ۴) فرانت‌اند

کارت «دستیار هوشمند بالینی» همان کارت است؛ فقط یک ردیف بالای پیام‌ها اضافه شد: Select گفتگوها (به‌روزشده با فعالیت) + دکمهٔ «گفتگوی جدید» (＋) + حذف (با ConfirmDialog). رفتار: بارگذاری اولیه → آخرین گفتگو انتخاب و پیام‌ها لود می‌شوند؛ ارسال بدون گفتگوی فعال → گفتگو ضمنی ساخته می‌شود؛ خطای 502 → پیام ورودی برمی‌گردد و خطا نمایش داده می‌شود (پیام سمت سرور ذخیره مانده و بعداً با reload دیده می‌شود)؛ toggle «بررسی ایمنی دارو» تسک ۱۴ بدون تغییر. حباب‌ها/disclaimer/RTL همان قبل.

## ۵) تست‌ها — مجموع **۲۲۹ passed** (مبنا: ۲۱۳، جدید: +۱۶)

ساخت با پیش‌فرض/عنوان دلخواه · 404 بیمار · ترتیب لیست بر اساس updated_at · ترتیب پیام‌ها + نقش‌ها (user/assistant) · 404 گفتگو · حذف + cascade · persist هر دو پیام (ردیف واقعی DB) · عنوان قطعی از پیام اول + بازنویسی‌نشدن عنوان دستی · **Context واقعی تسک ۹ در پیام** (شرایط موجود؛ شروع «Patient record (JSON):») + history خالی در تبادل اول + history کامل در تبادل دوم · سقف ۲۰ (۱۲ تبادل → ۲۲ پیام قبلی → قدیمی‌ترین ۲ حذف) · فلگ safety→پرامپت تسک ۱۴ / false→پرامپت عادی · **شکست AI: فقط پیام کاربر ماند، بدون assistant جعلی** · 503 با persist پیام کاربر · 422/404 · endpoint بدون-state تسک ۱۰ هنوز کار می‌کند.

همهٔ فراخوانی‌های LLM در تست‌ها mock هستند.

## ۶) Smoke زنده (:8003، کلید واقعی)

```
1) conversation=1 | title='گفتگوی جدید' ✓
2) send#1 → فراخوانی واقعی Gemini (لاگ) → 403 شبکه → 502 «پیام شما ثبت شد…» ✓
3) reload: title خودکار 'خلاصهٔ وضعیت بیمار؟' | messages=[user] — بدون assistant جعلی ✓
4) send#2 (safety=true) → 502 | پیام دوم هم persist (۲ پیام) ✓
5) list=['مشاوره دارویی','خلاصهٔ وضعیت بیمار؟'] | گفتگوی فعال‌تر اول ✓ | delete→204، remaining=1 ✓
6) cleanup ✓
```

**صادقانه:** پاسخ موفق واقعی Gemini روی این ماشین قابل‌تست نیست (بلاک شبکهٔ مستند تسک‌های ۱۲–۱۴)؛ مسیر موفق کامل با provider فرقی در ۱۶ تست پوشش داده شد؛ مسیر خطا زنده راستی‌آزمایی شد.

## ۷) راستی‌آزمایی‌ها

`pytest -q` → **229 passed** · `alembic upgrade/downgrade/upgrade/check` سبز · `tsc --noEmit` = 0 · `next build` ✓ · eslint فایل‌های تغییریافته بدون مشکل جدید.

## ۸) محدودیت‌ها

1. پاسخ موفق LLM روی این ماشین live نشد (با `AI_PROXY` فعال می‌شود).
2. بدون صفحه‌بندی برای گفتگوها/پیام‌ها (MVP؛ سقف history مدل ۲۰ است).
3. حذف/ویرایش تک‌پیام پیاده نشد (خارج از دامنه).
4. بدون احراز هویت/مالکیت — طبق تصمیم پروژه، فاز بعد.

## ۹) فایل‌ها

**ساخته‌شده:** `models/conversation.py` · `schemas/conversation.py` · `routes/conversations.py` · `alembic/versions/03378aed5376_*.py` · `tests/test_conversations_api.py` · گزارش
**تغییریافته:** `models/enums.py` (+ChatRole) · `models/patient.py` (+relationship) · `models/__init__.py` · `api/v1/api.py` (ثبت روتیر) · فرانت‌اند: `types.ts` · `api.ts` · `clinical-chat.tsx` · READMEها
**دست‌نخورده:** `routes/chat.py` و `schemas/chat.py` (تسک ۱۰) · `ai.py` · `patient_context.py` · تسک ۱۱ و ۱۴ · مایگریشن‌های قبلی
