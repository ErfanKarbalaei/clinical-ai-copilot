# گزارش تسک ۱۱ — ایمنی دارو (Prescription Safety)

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۱ (Task 11) — موتور قاعده‌محور قطعی ایمنی دارو + توضیح اختیاری LLM
- **تاریخ اجرا:** 2026-09-13
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۱۷۲ تست + smoke زنده)
- **کامیت:** هنوز کامیت نشده است

---

## ۱) معماری (طبق §11 مشخصات پروژه — بدون تغییر معماری کلی)

```
داروی کاندید (medication_id یا نام آزاد)
        ↓
موتور قاعده‌محور قطعی  (services/medication_safety.py — pure، بدون DB/شبکه)
        ↓  پایگاه قواعد نسخه‌بندی‌شدهٔ محلی (app/data/medication_rules.json)
هشدارهای قطعی (تداخل دارویی / تعارض حساسیت / درمان تکراری) — هرکدام با rule_id
        ↓  (اختیاری، explain=true)
توضیح فارسی توسط LLM — فقط «بازنمایی» هشدارهای قطعی؛ هرگز تولید/حذف هشدار
```

- **جدا از تولید آزاد LLM** (اصل §11): هشدارها فقط از قواعد می‌آیند؛ provider خراب/خاموش → هشدارها کامل می‌مانند و explanation=null می‌شود (تست‌شده).
- بدون جدول/مایگریشن جدید، بدون کپی داده — محاسبهٔ زنده روی regimen فعال + حساسیت‌های بیمار.

## ۲) API

`POST /api/v1/patients/{patient_id}/medications/check`
- ورودی: `{medication_id? | medication_name? (دقیقاً یکی), dosage?, explain?}`
- خروجی: `{patient_id, candidate_name, candidate_class_labels, candidate_covered, warnings[], rules_version, checked_at, explanation?, explanation_disclaimer?}`
- هر هشدار: `{warning_type, severity, title, detail, rule_id, involved[]}`
- 404 بیمار/داروی کاتالوگ ناموجود، 422 ورودی نامعتبر (پیام فارسی)

## ۳) پایگاه قواعد (v2026.09.1)

~۳۰ کلاس دارویی با نام‌های عمومی/برند انگلیسی + برندهای فارسی (گلوکوفاژ، بروفن، لازیکس…) · ۳۲ تداخل (از جمله triple-whammy کلیوی، وارفارین×آنتی‌بیوتیک‌ها، هیپرکالمی RAAS×پتاسیم، سندرم سروتونین SSRI×ترامادول، سرکوب تنفسی اوپیوئید×بنزودیازپین) · حساسیت متقاطع (پنی‌سیلین←سفالوسپورین) · درمان تکراری (با استثنای انسولین basal+bolus). نرمال‌سازی نام: یکسان‌سازی ی/ک عربی، حذف ZWNJ و ارقام/واحدهای دوز؛ تطبیق توکن‌محور امن.

## ۴) تست‌ها — مجموع **۱۷۲ passed** (+۳۱)

یکپارچگی KB (کلاس‌های ارجاع‌شده موجود، severities معتبر) · نرمال‌سازی فارسی/انگلیسی · تطبیق برند فارسی · ۹ سناریوی موتور (severe/moderate، triple، DOAC×وارفارین، حساسیت هم‌کلاس، cross-reactivity، تکراری، انسولین مجاز، ناشناخته بدون هشدار، ترتیب شدت) · ۹ تست API (تداخل/حساسیت/تکراری روی regimen واقعی، unknown، id کاتالوگ با داروی stopped، 422/404، explain با fake provider، explain با provider خراب → 200 و هشدارها سالم، چت تسک ۱۰ سالم).

## ۵) Smoke زنده (سرور :8003، بیمار seed علی)

```
1) Ibuprofen 400  → covered ✓ | NSAID | [moderate] INT-005 درگیر با Losartan
2) Amoxicillin 500 → [severe] XALL-000 منع مصرف — حساسیت پنی‌سیلین
3) Metformin 850  → [moderate] DUP-000 درمان تکراری (involved: Metformin 500)
4) explain=true   → HTTP 200 | هشدارها سالم [INT-005] | explanation: null (provider شبکه‌ای قطع)
5) 422/404ها ✓   6) چت تسک ۱۰ پاسخ‌گو (502 شبکه‌ای، نه 500) ✓
```

## ۶) فایل‌ها

**ساخته‌شده:** `app/data/medication_rules.json` · `services/medication_safety.py` · `schemas/medication_safety.py` · `routes/medication_safety.py` · `tests/test_medication_safety.py` · `scripts/smoke_medication_safety.py` · همین گزارش
**تغییریافته:** `api.py` (ثبت روتیر) · `config.py` (فقط رفع تورفتگی خط AI_MODEL که ویرایش دستی شکسته بود — مقدار gemini-3.6-flash کاربر حفظ شد) · `tests/test_chat_api.py` (دو assertion به ثابت‌های مدل — سازگار با gemini-3.6-flash) · READMEها

## ۷) محدودیت‌ها / پیشنهادها

1. قواعد آموزشی و منتخب‌اند — clinical-grade نیستند (بدون DrugBank/Micromedex لایسنس‌دار)؛ برای ارائهٔ دانشگاهی با همین ملاحظه مستند شده است
2. پوشش محدود به ~۳۰ کلاس پرکاربرد؛ داروهای ناشناخته → بدون هشدار (candidate_covered=false به کلاینت اعلام می‌شود)
3. بررسی فقط برای «کاندید × regimen فعال» است؛ اسکن کل regimen (جفت‌های موجود) follow-up خوبی است
4. UI فرانت‌ند برای این endpoint عمداً در این تسک ساخته نشد (طبق محدودیت تسک) — گام بعدی طبیعی: نمایش هشدارها هنگام افزودن دارو
5. در صورت نیاز به عمق بیشتر: اتصال به منبع RxNorm/openFDA برای استانداردسازی نام (طبق نقشهٔ اصلی §10) قابل افزودن است
