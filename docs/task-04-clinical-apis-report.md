# گزارش تسک ۴ — APIهای اطلاعات بالینی بیمار

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۴ (Task 4) — APIهای Conditions ، Allergies ، Patient Medications + به‌روزرسانی Overview
- **تاریخ اجرا:** 2026-08-25
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۶۳ تست + اجرای زنده روی دادهٔ seed)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) endpointهای ساخته‌شده (۱۶ endpoint جدید)

### Conditions
| متد | مسیر | توضیح |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/conditions` | ثبت مشکل بالینی (201؛ 404 اگر بیمار نباشد) |
| GET | `/api/v1/patients/{id}/conditions` | فهرست — فعال‌ها اول، سپس جدیدترین شروع |
| GET | `/api/v1/conditions/{id}` | دریافت (404) |
| PATCH | `/api/v1/conditions/{id}` | به‌روزرسانی جزئی |
| DELETE | `/api/v1/conditions/{id}` | حذف (204) |

### Allergies
| متد | مسیر | توضیح |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/allergies` | ثبت حساسیت (201) |
| GET | `/api/v1/patients/{id}/allergies` | فهرست — شدیدترها اول |
| GET | `/api/v1/allergies/{id}` | دریافت (404) |
| PATCH | `/api/v1/allergies/{id}` | به‌روزرسانی جزئی |
| DELETE | `/api/v1/allergies/{id}` | حذف (204) |

### Patient Medications
| متد | مسیر | توضیح |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/medications` | افزودن دارو — با `medication_id` **یا** `medication_name` (کاتالوگ بازاستفاده/ایجاد می‌شود) |
| GET | `/api/v1/patients/{id}/medications` | فهرست — active→stopped→completed، جدیدترین شروع اول؛ فیلتر `?status=` |
| GET | `/api/v1/patient-medications/{id}` | دریافت با اطلاعات کاتالوگ دارو (404) |
| PATCH | `/api/v1/patient-medications/{id}` | دوز/تناوب/وضعیت/توضیحات — توقف = `{"status":"stopped"}` بدون حذف تاریخچه |
| DELETE | `/api/v1/patient-medications/{id}` | حذف فیزیکی رکورد (204) |

### Patient Overview
| متد | مسیر | توضیح |
| --- | --- | --- |
| GET | `/api/v1/patients/{id}/overview` | `{patient, conditions, active_medications, allergies, recent_lab_results(۵), recent_clinical_notes(۵)}` — فقط دادهٔ ساخت‌یافتهٔ دیتابیس، بدون خلاصهٔ هوش مصنوعی |

> **نکته:** متن تسک فرض کرده بود Overview در تسک ۳ ساخته شده — چنین نبود؛ در همین تسک ساخته شد.

## ۲) فایل‌های ساخته/تغییریافته

**ساخته‌شده:** `app/api/v1/dependencies.py` (وابستگی مشترک `patient_from_id`) · `app/services/medications.py` (`get_or_create_medication`) · `app/schemas/{condition,allergy,medication,lab_result,clinical_note}.py` · `app/api/v1/routes/{conditions,allergies,medications}.py` · `tests/test_{conditions,allergies,medications,patient_overview}_api.py` · همین گزارش
**تغییریافته:** `app/api/v1/routes/patients.py` (بازنویسی: استفاده از وابستگی مشترک + endpointی Overview) · `app/api/v1/api.py` · `app/schemas/patient.py` (+`PatientOverviewResponse`) · `backend/README.md` · `README.md` ریشه · `docs/README.md`

## ۳) تست‌ها

**۳۶ تست جدید** (شرایط ۸، حساسیت ۹، دارو ۱۴، Overview ۵) — مجموع: **۶۳ passed** (۶.۹ ثانیه). تمام suite اجرا شد، نه فقط تست‌های تسک ۴.

## ۴) تصمیم‌های مهندسی مهم

1. **وابستگی مشترک `patient_from_id`** — اعتبارسنجی وجود بیمار در همهٔ مسیرهای تودرتو بدون تکرار کد؛ patients.py تسک ۳ هم به آن مهاجرت کرد (تست‌های تسک ۳ همچنان سبز).
2. **ارجاع دارو با id یا نام (دقیقاً یکی)** — `model_validator` پیامی فارسی برای موارد نقض می‌دهد (422)؛ تطبیق نام case-insensitive و بازاستفاده از ردیف کاتالوگ (`services/medications.py`) — اولین استفادهٔ واقعی از لایهٔ services.
3. **مرتب‌سازی قطعی برای UI بالینی** — داروها: active→stopped→completed سپس `start_date DESC NULLS LAST` سپس id؛ شرایط: فعال اول؛ حساسیت‌ها: severe→moderate→mild→unknown.
4. **تاریخچهٔ دارو حذف نمی‌شود** — توقف با PATCH است؛ DELETE (حذف فیزیکی) در توضیح endpoint به‌عنوان آخرین گزینه ذکر شده.
5. **nested listها آرایهٔ ساده، بدون wrapper** — برخلاف فهرست صفحه‌بندی‌شدهٔ بیماران (`{items,total}`)؛ حجم هر بیمار محدود است.
6. **بدون تغییر schema** — «diagnosed_at» متن تسک همان `onset_date` مدل است؛ «status» حساسیت و «route» دارو در مدل وجود ندارند و طبق بخش ۸ تسک، ستونی اضافه نشد.
7. **409 فقط برای تعارض واقعی** — در این سه منبع قید یکتایی وجود ندارد؛ فقط patients کد 409 دارد (تسک ۳).
8. **`?status=` فقط مقادیر enum معتبر** — مقدار نامعتبر خودکار 422.

## ۵) راستی‌آزمایی زنده (نمونه‌ها از خروجی واقعی)

```json
GET /api/v1/patients/1/overview →
  conditions: ["دیابت نوع ۲ (Type 2 Diabetes)", "پرفشاری خون (Hypertension)"]
  active_medications: ["Metformin 500", "Losartan 50"]
  allergies: [("پنی‌سیلین (Penicillin)", "severe")]
  recent_lab_results: [("LDL","140","abnormal"), ("FBS","168","abnormal"), ("HbA1c","8.2","abnormal")]

POST /api/v1/patients/2/medications {"medication_name":"Atorvastatin 20","dosage":"20 mg","frequency":"هر شب"} → 201
  {"id":5,"medication":{"id":5,"name":"Atorvastatin 20",...},"status":"active",...}
PATCH /api/v1/patient-medications/5 {"status":"stopped","end_date":"2026-08-10"} → 200
GET  /api/v1/patients/2/medications?status=stopped → [{"medication":{"name":"Atorvastatin 20"},"status":"stopped"}]  // تاریخچه ماند

404 → {"detail":"بیمار یافت نشد."} / {"detail":"مشکل بالینی یافت نشد."} / {"detail":"داروی بیمار یافت نشد."}
```

OpenAPI: همهٔ endpointها دارای `summary` ، `response_model` ، `responses` (404/409) و توضیحات فارسی/انگلیسی‌اند — از طریق `http://localhost:8000/docs` قابل مشاهده.

## ۶) هشدارها / نکات

1. متن تسک «diagnosed_at» و «status» (حساسیت) و «route» (دارو) را ذکر کرده بود که در مدل تسک ۲ وجود ندارند — طبق بخش ۸ (عدم تغییر schema) نگاشت به فیلدهای موجود (`onset_date` و...) انجام شد؛ اگر بعداً فیلدی واقعاً لازم شد با مایگریشن اضافه می‌شود.
2. FastAPI 0.141 روتیرهای include شده را به‌صورت تو در تو (`_IncludedRouter`) نگه می‌دارد — سرویس‌دهی کاملاً درست است؛ فقط introspection سادهٔ `app.routes` مسیرها را نمایش نمی‌دهد.
3. تست‌های تست JSON فارسی inline در Git Bash ویندوز همچنان باید از فایل استفاده کنند (مسئلهٔ شل، نه API).
4. هشدار اطلاعاتی Starlette (httpx→httpx2) — بدون اثر.
5. پس از تست زنده، دیتابیس seed با `--reset` به حالت اولیه بازگردانده شد؛ کانتینر postgres در پایان متوقف شد.

## ۷) گام بعدی

طبق دستورالعمل **متوقف می‌شویم**. پیشنهاد برای تسک ۵: فرانت‌اند — فهرست بیماران و صفحهٔ بالینی بیمار (مصرف Overview).
