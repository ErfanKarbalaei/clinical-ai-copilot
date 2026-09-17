# گزارش تسک ۱۸ — احراز هویت و کنترل دسترسی

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۸ (Task 18) — Authentication & Authorization for MVP
- **تاریخ اجرا:** 2026-09-17
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۳۲۷ تست + smoke واقعی)
- **کامیت:** `13f5784`

---

## ۱) معماری (حداقلی — روی choke point موجود)

```
Authorization: Bearer <JWT>
      ↓ get_current_user (decode → user فعال یا 401)
      ↓ patient_from_id (همان dependency همهٔ routeهای تودرتو)
        ├─ بیمار ناشناخته → 404 (semantics قبل حفظ شد)
        └─ ensure_patient_access:
             admin → همه‌جا مجاز
             doctor → فقط ردیف patient_user_access
      ↓ منابع فرزند (سند/گفتگو/یادداشت صوتی/...): دسترسی از طریق
        بیمارِ مالک، در همان helperهای _get_X_or_404 — قبل از هر کاری
        (تولید URL امضاشدهٔ دانلود فقط بعد از authorization)
```

بدون IAM پیچیده، بدون OAuth، بدون IDP خارجی — JWT + bcrypt + یک جدول انتساب.

## ۲) مدل داده + Migration

- `users`: id, email (unique index), password_hash (bcrypt — هرگز plaintext/در پاسخ/در لاگ), full_name, role (enum بومی `user_role`: doctor|admin), is_active, timestamps
- `patient_user_access`: id, patient_id (FK CASCADE), user_id (FK CASCADE), timestamps + **unique(patient_id, user_id)**
- Migration `9a1c78a56f1a` (بعد از ab22d66552c2) — چرخهٔ upgrade→downgrade→upgrade ✓ + `alembic check` پاک

## ۳) API

| متد | مسیر | رفتار |
|---|---|---|
| POST | `/auth/register` | 201؛ همیشه doctor (admin-self-register → 403 فارسی)؛ تکراری email → 409 |
| POST | `/auth/login` | `{access_token, token_type: bearer}`؛ پیام **یکسان** 401 برای email غلط و گذرواژهٔ غلط؛ حساب غیرفعال → 401 |
| GET | `/auth/me` | کاربر جاری (بدون hash) |

`GET /health` عمومی ماند. همهٔ endpointهای بالینی محافظت‌شده. قواعد دسترسی: admin همه؛ doctor فقط منتسب‌ها؛ **ساخت بیمار توسط doctor = انتساب خودکار**؛ لیست بیماران بر اساس role فیلتر می‌شود.

## ۴) امنیت پیاده‌شده

- رمزها: bcrypt (`core/security.py` — `hash_password`/`verify_password` ایزوله و تست‌پذیر)
- JWT: PyJWT HS256؛ `JWT_SECRET_KEY`/`JWT_ALGORITHM`/`JWT_EXPIRE_MINUTES` از env (پیش‌فرض dev-only با هشدار تغییر در `.env.example`)؛ هرگز در سورس فرانت
- 401 بدون لو دادن جزئیات؛ 403 فارسی «شما به پروندهٔ این بیمار دسترسی ندارید.»
- منابع فرزند با id حدسیِ بیمار دیگر → 403 (تست‌شده برای سند/دانلود/گفتگو/یادداشت صوتی/دارو/شرایط/آلرژی)
- endpoint تسک ۱۷ (agent) پشت همان patient_from_id — authorization **قبل از** هر فراخوانی MCP

## ۵) فرانت‌اند

`/login` (فارسی RTL) · `lib/auth.ts` (توکن در localStorage + cookie برای forwarding) · `api.ts`: کلاینت → `Authorization` از localStorage؛ سرورکامپوننت‌ها → cookie به Bearer (بک‌اند header-only ماند) · 401 در کلاینت → پاک‌کردن توکن + redirect به `/login` · صفحات بیمار: 401 → redirect، 403 → پیام فارسی · دکمهٔ «خروج» در هدر فهرست بیماران.

## ۶) سازگاری با تسک‌های قبل

۲۷۱ تست موجود **یک خط تغییر نکردند** — `conftest.api_client` همه را با یک کاربر admin اجرا می‌کند (ادمین از انتساب عبور می‌کند؛ رفتار کسب‌وکاری همهٔ endpointها همان قبل است). پوشش auth/دسترسی در ۲ فایل تست جدید با dependency واقعی. تسک ۱۰/۱۱/۱۴/۱۵/۱۶/۱۷ فقط در امضای routeها (+`user`) تغییر سطحی خوردند؛ منطق‌شان دست‌نخورده.

## ۷) Seed کاربران دمو (فقط توسعه)

`python scripts/seed.py` (idempotent؛ حتی وقتی دادهٔ بالینی هست، کاربران را می‌سازد):
`admin@example.com / admin-dev-12345` · `doctor@example.com / doctor-dev-12345` (دکتر دمو به همهٔ بیماران seed دسترسی می‌گیرد) — در `.env.example` مستند با هشدار dev-only.

## ۸) تست‌ها — **327 passed** (+۵۶)

Auth (۲۴): ثبت‌نام/تکراری/ردِ ادمین · hash/verify · login موفق/غلط (پیام یکسان) · غیرفعال (login+token) · me با/بدون توکن · JWT خراب/منقضی · endpoint محافظت‌شده بدون توکن · health عمومی.
Authorization (۳۲): ماتریس doctor/admin/anon روی ۱۰ route تودرتو · chat/ai-safety/agent · دانلود سند (۴۰۳ قبل از presigned) · conversation/voice-note فرزندِ بیمار دیگر · لیست role-scoped · انتساب خودکار هنگام ساخت.

## ۹) Smoke واقعی

seed ✓ → doctor login/me (بدون hash) ✓ → لیست فقط ۱ بیمار منتسب + context 200 ✓ → بیمار خصوصی ادمین: doctor 403 فارسی / admin 200 ✓ → سند خصوصی: doctor 403 قبل از presigned / admin 307 ✓ → conversation و agent بیمار غیرمجاز 403 ✓ → گذرواژهٔ غلط 401 / ثبت‌نام 201 ✓.

## ۱۰) محدودیت‌ها

1. بدون refresh token (MVP؛ انقضا = ورود دوباره — پیش‌فرض ۸ ساعت)
2. cookie توکن غیر-HttpOnly (لازم برای forwarding سرورکامپوننت‌های Next؛ trade-off مستند)
3. ثبت‌نام باز فقط نقش doctor؛ ادمین فقط از seed
4. 404 قبل از 403 (semantics موجود حفظ شد؛ ضد enumeration کامل نشده — عمداً)
5. UI تعاملی login در مرورگر live تست نشد (build + کد بررسی شد؛ backend کامل live شد)
6. بدون rate-limit روی login (خارج از MVP)

## ۱۱) فایل‌ها

**اضافه:** `core/security.py` · `models/user.py` · `models/patient_user_access.py` · `schemas/auth.py` · `routes/auth.py` · `alembic/versions/9a1c78a56f1a_*.py` · `tests/test_auth_api.py` · `tests/test_patient_access_control.py` · `frontend/src/lib/auth.ts` · `frontend/src/app/login/page.tsx` · `frontend/src/components/shared/logout-button.tsx` · همین گزارش
**تغییر:** `dependencies.py` · ۶ route فرزند + `patients.py` · `config.py` · `enums.py`/`patient.py`/`models/__init__` · `conftest.py` · `seed.py` · `api.py` · `requirements.txt` (+bcrypt, PyJWT, email-validator) · فرانت `api.ts` + دو صفحهٔ بیمار · `.env.example` · READMEها
