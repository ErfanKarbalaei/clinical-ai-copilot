# گزارش تسک ۱۶ — شواهد و اسناد منبع

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۶ (Task 16) — Evidence & Source Documents
- **تاریخ اجرا:** 2026-09-17
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده (۲۴۴ تست + build فرانت‌اند + smoke زنده با آبجکت واقعی MinIO)
- **کامیت:** هنوز کامیت نشده است

> **تأکید صریح:** تسک ۱۶ «ردیابی پاسخ‌ها به رکوردهای واقعی بیمار + دسترسی به فایل اصلی سند» را فراهم می‌کند و **citation ادبیات پزشکی خارجی نیست** — بدون PubMed/FDA/RxNorm/web search/RAG (خارج از دامنه).

---

## ۱) چه چیزی پیاده شد

پاسخ‌های چت ماندگار (تسک ۱۵) حالا **قابل‌ردیابی به رکوردهای واقعی بیمار** هستند: هر آیتم Context تسک ۹ یک شناسهٔ پایدار شواهد می‌گیرد، مدل به استناد آن‌ها پاسخ می‌دهد، بک‌اند هر استناد را اعتبارسنجی می‌کند، و شواهدِ معتبر همراه پیام دستیار ذخیره می‌شوند. برای شواهدِ سند‌محور، پزشک با «مشاهده سند اصلی» فایل اصلی را از **همان endpoint امن موجود** باز می‌کند.

## ۲) معماری شواهد

```
Context تسک ۹ (زنده، در لحظهٔ هر پیام — بدون snapshot)
   ↓ evidence.build_evidence_index / annotate_context
هر رکورد → شناسهٔ پایدار از PK واقعی (MED-42، LAB-31، DOC-123، …)
   ↓ + history (۲۰ پیام) + پیام جار → همان provider Gemini
مدل: {"answer": "…", "evidence": ["LAB-31", "DOC-123"]}
   ↓ evidence.parse_evidence_answer (تحمل fence/nثر؛ نثر → پاسخ بدون شواهد)
   ↓ evidence.validate_evidence (فقط شناسه‌های موجود در Context همین بیمار)
شواهد معتبر → EvidenceItem{source_id, source_type, description, document_id}
   ↓ ذخیره در conversation_messages.evidence (JSONB) — بدون هیچ URL
   ↓ رابط کاربری: بلوک «شواهد بالینی» + «مشاهده سند اصلی»
```

## ۳) قالب شناسهٔ شواهد

| بخش Context | پیشوند | source_type |
|---|---|---|
| medications | `MED-<patient_medication.id>` | medication |
| allergies | `ALLERGY-<id>` | allergy |
| conditions | `COND-<id>` | condition |
| lab_results | `LAB-<id>` | lab |
| documents | `DOC-<id>` | document |
| clinical_notes | `NOTE-<id>` | clinical_note |
| voice_notes | `VOICE-<id>` | voice_note |

شناسه‌ها **فقط** از primary keyهای واقعی دیتابیس ساخته می‌شوند — نه تصادفی، نه جعل.

## ۴) اعتبارسنجی بک‌اند (هرگز به مدل اعتماد نمی‌شود)

هر شناسهٔ برگشتی مدل باید در index شواهدِ همین بیمار موجود باشد؛ وگرنه **حذف و لاگ** می‌شود (هرگز به یک منبع معتبرنما تبدیل نمی‌شود): شناسهٔ ناشناخته · رشتهٔ URL · PMID جعلی · شناسهٔ بیمار دیگر (تست امنیتی cross-patient) · تکراری‌ها (dedup) · سقف دفاعی ۱۰ مورد. توصیف/type/document_id هر آیتم **همیشه از بک‌اند** می‌آید، نه مدل. پاسخ نثر (بدون JSON معتبر) → همان متن به‌عنوان پاسخ + بدون شواهد (هیچ چیز جعل نمی‌شود، پاسخ قابل‌استفاده هم دور ریخته نمی‌شود).

## ۵–۷) رزولوشن سند + Object Storage + URL امن

- `document_id` فقط وقتی پر می‌شود که رابطهٔ **واقعی** وجود داشته باشد: خودِ سند، یا آزمایش از طریق FK موجود `lab_results.document_id` (رابطهٔ جعل‌شده ساخته نشد).
- فایل اصلی از طریق **`GET /documents/{id}/download` موجود (تسک ۶)** باز می‌شود: 307 → presigned کوتاه‌مدت (۳۶۰۰s). **بدون endpoint دوم، بدون storage دوم** (تصمیم §17: از API تکراری پرهیز شد).
- مدل هرگز URL نمی‌بیند/نمی‌سازد؛ **هیچ URL در PostgreSQL ذخیره نمی‌شود** — فقط ارجاع پایدار؛ URL در لحظهٔ کلیک ساخته می‌شود (§16 برآورده می‌شود چون اصلاً URL persist نمی‌کنیم).
- نکتهٔ فنی صادقانه: access-key-id در scope credential هر URL امضاشدهٔ S3 تعبیه شده (ذات الگوریتم، همان AWS) — **secret هرگز** ظاهر نمی‌شود؛ امضا بدون آن بی‌ارزش و URL موقت است؛ در استقرار واقعی key-id حدس‌زدنیِ dev (`minioadmin`) جایگزین می‌شود.

## ۸) ادغام با چت ماندگار + ایمنی دارو

- endpoint `POST /conversations/{id}/messages` حالا: annotate → پرامپت evidence-دار → parse/validate → persist پاسخ + شواهد.
- پرامپت‌ها **ترکیب** پرامپت‌های موجود هستند (`ai.SYSTEM_PROMPT` / `MEDICATION_SAFETY_CHAT_PROMPT` تسک ۱۴ + قواعد شواهد) — نه بازنویسی؛ تمایز صریح «شواهد بیمار» vs «دانش عمومی پزشکی» (ادعای تداخل دارویی با citation بیماری اثبات نمی‌شود).
- medication_safety=true → `EVIDENCE_SAFETY_SYSTEM_PROMPT`؛ شواهد همان مسیر اعتبارسنجی.
- **تسک ۱۰ (بدون-state) دست‌نخورده** (تصمیم مستند §21 — قراردادش پایدار ماند؛ شواهد فقط در چت ماندگار). یک تست تسک ۱۵ (انتظار پرامپت قدیمی) عمداً به قرارداد جدید به‌روز شد.

## ۹) فرانت‌اند

حباب دستیار: متن پاسخ + بلوک ثانویهٔ «شواهد بالینی» — آیکون بر اساس نوع (دارو/آلرژی/آزمایش/سند/یادداشت/صوت/تشخیص) + توصیف خوانا (اصلی) + شناسهٔ پایدار به‌صورت محو و LTR (برای ردیابی) + برای آیتم‌های سندمحور لینک «مشاهده سند اصلی ←» به endpoint موجود (target=_blank). پیام‌های قدیمی بدون شواهد بی‌تغییر رندر می‌شوند. هیچ object key در UI نیست؛ URL در فرانت ساخته نمی‌شود.

## ۱۰) دیتابیس

تنها تغییر: `conversation_messages.evidence` — JSONB nullable (لیست EvidenceItem). Migration `ab22d66552c2` (بعد از 03378aed5376) — چرخهٔ upgrade→downgrade→upgrade سبز + `alembic check` پاک. بدون جدول/enum جدید.

## ۱۱) تست‌ها — مجموع **۲۴۴ passed** (مبنا: ۲۲۹، جدید: +۱۵)

index از PKهای واقعی · annotate در پیام AI («Patient record (JSON):» + evidence_id) · شواهد معتبر با type/توصیف غنی‌شده · حذف LAB-999/URL/PMID/شناسهٔ بیمار دیگر · dedup و سقف · parse ساخت‌یافته (fence) و fallback نثر · DOC → document_id درست + endpoint موجود 307 (بدون follow — آبجکت فیک) · LAB با FK واقعی → سند منبع · persist + reload بدون URL · پیام قدیمی بدون شواهد → [] · پرامپت safety ترکیبی + قواعد (URL/PubMed ممنوع) · تسک ۱۰ بدون تغییر · پاسخ نثر بدون شواهد. همهٔ LLMها mock.

## ۱۲) راستی‌آزمایی‌ها

`pytest -q` → **244 passed** · migration cycle + `alembic check` سبز · `tsc` = 0 · `next build` ✓ · eslint فایل‌های تغییریافته پاک.

## ۱۳) Smoke زنده (:8003 — با آبجکت واقعی MinIO)

```
1) بیمار + دارو + سند واقعی (PDF واقعی در MinIO از طریق API واقعی) ✓
2) index شواهد از رکوردهای واقعی: ['DOC-6','MED-8'] | evidence_id داخل پیام AI ✓
3) دانلود سند موجود: 307 → presigned → بایت‌به‌بایت اصیل ✓ | موقت (X-Amz-Expires) ✓
4) ارسال پیام → Gemini واقعی → 403 بلاک شبکه → 502 تمیز | پیام کاربر ماند | بدون assistant جعلی ✓
5) cleanup ✓
```

**صادقانه:** پاسخ موفق واقعی Gemini روی این ماشین live نشد (بلاک مستند شبکه)؛ مسیر شواهدِ کامل با provider فرقی در ۱۵ تست پوشش شد؛ آنچه live شد: ساخت شناسه‌های واقعی، annotating پیام، دسترسی byte-identical به فایل اصلی از MinIO، و مسیر خطا.

## ۱۴) محدودیت‌ها

1. citation ادبیات پزشکی خارجی عمداً نیست (فاز آیندهٔ evidence retrieval).
2. endpoint دانلود سند سراسری است (بدون auth عمومی پروژه)؛ مسیر شواهد فقط شناسه‌های همین بیمار را افشا می‌کند — auth کامل فاز بعد.
3. fallback نثر: پاسخ بدون شواهد نمایش داده می‌شود (تصمیم UX مستند؛ در T14 ساخت‌یافته 502 می‌دهد چون endpoint ساخت‌یافته است).
4. evidence روی پیام‌های قبل از تسک ۱۶ خالی است (رندر عادی).

## ۱۵) فایل‌ها

**ساخته‌شده:** `services/evidence.py` · `alembic/versions/ab22d66552c2_*.py` · `tests/test_evidence_api.py` · گزارش
**تغییریافته:** `models/conversation.py` (+ستون JSONB) · `schemas/conversation.py` (+EvidenceItemResponse و فیلد/validator) · `routes/conversations.py` (جریان شواهد) · `tests/test_conversations_api.py` (به‌روزسازی قرارداد پرامپت) · فرانت‌اند: `types.ts` · `clinical-chat.tsx` · READMEها
**دست‌نخورده:** `ai.py` · `patient_context.py` · تسک ۱۰/۱۱/۱۴ · سرویس storage · endpoint دانلود سند (فقط مصرف شد)
