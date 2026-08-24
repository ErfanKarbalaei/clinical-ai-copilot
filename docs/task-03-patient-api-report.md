# گزارش تسک ۳ — API بیمار (Patient CRUD API)

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۳ (Task 3) — endpointهای CRUD بیمار روی مدل دادهٔ تسک ۲
- **تاریخ اجرا:** 2026-08-25
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (تست + اجرای زنده)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) endpointهای ساخته‌شده

| متد | مسیر | توضیح | کدهای وضعیت |
| --- | --- | --- | --- |
| `POST` | `/api/v1/patients` | ایجاد بیمار | 201 / 409 (کد ملی تکراری) / 422 |
| `GET` | `/api/v1/patients` | فهرست بیماران با `?q=` (جست‌وجوی نام/نام خانوادگی/کد ملی)، `?limit=` (۱ تا ۱۰۰، پیش‌فرض ۲۰) و `?offset=` | 200 |
| `GET` | `/api/v1/patients/{id}` | دریافت یک بیمار | 200 / 404 |
| `PATCH` | `/api/v1/patients/{id}` | به‌روزرسانی جزئی (فقط فیلدهای ارسالی) | 200 / 404 / 409 / 422 |
| `DELETE` | `/api/v1/patients/{id}` | حذف بیمار + همهٔ داده‌های بالینی مرتبط (cascade) | 204 / 404 |

پاسخ فهرست: `{"items": [...], "total": n}`. اعتبارسنجی: `national_code` دقیقاً ۱۰ رقم و یکتا؛ `date_of_birth` باید در گذشته باشد. پیام‌های خطای سفارشی (404/409) **فارسی**اند تا مستقیم در UI فارسی نمایش داده شوند.

## ۲) فایل‌های ساخته/تغییریافته

**ساخته‌شده:**
- `backend/app/schemas/patient.py` — `PatientCreate` / `PatientUpdate` / `PatientResponse` / `PatientListResponse`
- `backend/app/api/v1/routes/patients.py` — روتیر CRUD
- `backend/tests/test_patients_api.py` — ۱۴ تست API
- همین گزارش

**تغییریافته:**
- `backend/app/api/v1/api.py` — ثبت روتیر patients
- `backend/tests/conftest.py` — فیکسچر `api_client` (override وابستگی `get_db` به سشن ایزولهٔ تست)
- `backend/README.md` (جدول endpointها)، `README.md` ریشه (وضعیت)، `docs/README.md`

## ۳) تست‌های اضافه‌شده و نتایج

۱۴ تست API جدید (create موفق/حداقلی/کد نامعتبر/فیلد اجباری/تکراری، get موجود/غایب، صفحه‌بندی، جست‌وجو، patch جزئی/غایب/تکراری، delete موفق/غایب).

`python -m pytest` → **۲۷ passed** در ~۱.۲ ثانیه (۳ health + ۷ مدل + ۳ seed + ۱۴ API).

تست‌های API روی همان دیتابیس `_test` ایزوله اجرا می‌شوند و بدون PostgreSQL خودکار skip می‌گردند.

## ۴) نمونهٔ درخواست/پاسخ (خروجی واقعی از اجرای زنده)

### ایجاد بیمار
```http
POST /api/v1/patients
{"first_name":"نگار","last_name":"سلطانی","national_code":"0055555555",
 "date_of_birth":"1993-02-08","gender":"female"}
```
```json
HTTP 201
{"first_name":"نگار","last_name":"سلطانی","national_code":"0055555555",
 "date_of_birth":"1993-02-08","gender":"female","phone":null,"address":null,
 "id":4,"created_at":"2026-08-24T22:43:01.735161Z","updated_at":"2026-08-24T22:43:01.735161Z"}
```

### فهرست با جست‌وجو (دادهٔ seed)
```http
GET /api/v1/patients?q=مریم
```
```json
HTTP 200
{"items":[{"first_name":"مریم","last_name":"احمدی","national_code":"0023456789",
 "date_of_birth":"1985-11-02","gender":"female","phone":null,"address":null,
 "id":2,"created_at":"...","updated_at":"..."}],"total":1}
```

### به‌روزرسانی جزئی
```http
PATCH /api/v1/patients/4  →  {"phone":"09125550000"}
```
```json
HTTP 200  — فقط phone تغییر کرد؛ بقیهٔ فیلدها دست‌نخورده
```

### خطاها
```json
HTTP 409  {"detail":"این کد ملی قبلاً برای بیمار دیگری ثبت شده است."}
HTTP 404  {"detail":"بیمار یافت نشد."}
HTTP 422  (کد ملی نامعتبر — جزئیات اعتبارسنجی Pydantic)
HTTP 204  (حذف موفق — بدون بدنه)
```

## ۵) تصمیم‌های مهندسی

1. **PATCH به‌جای PUT** — به‌روزرسانی جزئی با `exclude_unset`؛ ساده‌تر و کافی برای MVP.
2. **پیام خطای فارسی فقط برای خطاهای سفارشی (404/409)** — این پیام‌ها مستقیم در UI فارسی نمایش داده می‌شوند؛ خطاهای 422 ساختار استاندارد Pydantic باقی می‌مانند.
3. **جست‌وجو با `ILIKE` روی نام/نام خانوادگی/کد ملی** — بدون وابستگی جدید (بدون pg_trgm/فول‌تکست) تا وقتی نیاز واقعی شود.
4. **`limit` حداکثر ۱۰۰** — جلوگیری از کوئری‌های بی‌انتها.
5. **دسترسی مستقیم DB در routeها** — CRUD سادهٔ بدون منطق تجاری؛ لایهٔ services برای زمانی که منطق واقعی (پردازش سند، STT و...) بیاید باقی مانده است.
6. **`PastDate` برای تاریخ تولد** — اعتبارسنجی دامنه‌ای با یک نوع آمادهٔ Pydantic.
7. **rollback صریح بعد از IntegrityError** قبل از raise — سشن برای درخواست‌های بعدی سالم می‌ماند.

## ۶) هشدارها

1. **curl در Git Bash ویندوز با JSON فارسی inline مشکل کدگذاری دارد** (`HTTP 400: error parsing the body`) — مشکل از shell است نه API؛ با `--data-binary @file.json` درست کار می‌کند. تست‌ها (TestClient) هم UTF-8 را درست می‌فرستند.
2. هشدار اطلاعاتی Starlette (httpx→httpx2) همچنان هست — بدون اثر.
3. endpointهای موجودیت‌های وابسته (conditions/medications/...) عمداً ساخته نشدند — تسک بعدی.

## ۷) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**. پیشنهاد برای تسک ۴: endpointهای داده‌های بالینی مرتبط (conditions/allergies/patient_medications) یا شروع صفحهٔ فهرست بیماران در فرانت‌اند.
