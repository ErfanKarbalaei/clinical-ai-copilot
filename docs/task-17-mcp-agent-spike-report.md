# گزارش تسک ۱۷ — Spike معماری MCP + Clinical AI Agent

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱۷ (Task 17) — Local MCP + Clinical AI Agent Architecture Spike
- **تاریخ اجرا:** 2026-09-17
- **وضعیت:** ✅ Spike تکمیل‌شده (۲۷۱ تست + MCP زنده با دادهٔ واقعی + ارزیابی صادقانه)
- **کامیت:** نشده (طبق دستور)

---

## ۱) هدف

فهمیدن اینکه آیا MCP + Agent واقعاً orchestration دسترسی AI به دادهٔ بیمار را **بهتر و ساده‌تر** می‌کند یا خیر — نه صرفاً نصب MCP. این یک spike است: معماری فعلی دست‌نخورده ماند و لایهٔ جدید کنارش ساخته شد.

## ۲) معماری قبل (تسک‌های ۹–۱۶)

چت ماندگار: هر پیام → کل Context بیمار (تسک ۹، سقف‌دار) + ۲۰ پیام history → Gemini → پاسخ + شواهد اعتبارسنجی‌شده (تسک ۱۶). Context همیشه **کامل** ارسال می‌شود؛ انتخاب داده با سؤال تنظیم نمی‌شود.

## ۳) معماری بعد (تسک ۱۷)

```
User → POST /patients/{id}/agent/chat
        ↓ سمت بک‌اند (مسیر جدا از چت ماندگار)
Gemini (همان provider) → انتخاب ۱–۳ ابزار فقط-خواندنی (JSON-plan متنی)
        ↓ patient_id همیشه از route تزریق می‌شود — مدل هرگز id نمی‌دهد
MCP Server محلی (subprocess استاندارد stdio، SDK رسمی mcp 2.2.0)
        ↓ ابزارها = همان build_patient_context/build_timeline تسک ۹
PostgreSQL واقعی → نتیجه → Gemini (پاسخ نهایی grounded)
```

مرزبندی حفظ شد: **AI=استدلال · MCP=رابط کنترل‌شدهٔ ابزار · بک‌اند=امنیت/قواعد · DB=منبع حقیقت · MinIO=فایل اصلی (هرگز در MCP)**

## ۴) MCP چیست و نقشش

Model Context Protocol = پروتکل استاندارد (JSON-RPC روی stdio) برای اینکه مدل/عامل از طریق «ابزار»های تعریف‌شده با سیستم‌های داده حرف بزند. اینجا: یک **لایهٔ Tool Access فقط-خواندنی** بین Agent و لایهٔ دادهٔ موجود — نه جایگزین بک‌اند.

## ۵–۶) ابزارها و اتصال به بک‌اند

۶ ابزار: `get_patient` · `get_patient_context` · `get_patient_labs` · `get_patient_medications` · `get_patient_documents` · `get_patient_timeline`. همگی `_*_impl(db, patient_id)` با session قابل‌تزریق → **صفر منطق تکراری**؛ همه چیز از `build_patient_context`/`build_timeline` تسک ۹ می‌آید (نکتهٔ trade-off: ابزارهای تخصصی هم همان Context کامل را می‌سازند و slice می‌کنند — در پذیرش واقعی باید loader های بخش‌ای استخراج شوند).

## ۷) اتصال Agent به Gemini

همان `ai.get_provider()` (`gemini-3.6-flash`) — **بدون کلاینت/SDK/provider جدید**. چون abstraction فعلی function-calling بومی ندارد، انتخاب ابزار با **JSON-plan متنی** انجام می‌شود (دو فراخوانی: planner → answerer). این تصمیم آگاهانه برای دست‌نخوردن ماندن `ai.py` است.

## ۸–۹) انتخاب ابزار و Multi-Tool

Planner پرامپت می‌گیرد و JSON برمی‌گرداند: `{"tools":[...]}` یا `{"answer":"..."}`. نام‌های ناشناخته حذف می‌شوند؛ سقف ۳ ابزار؛ Multi-Tool تست‌شده (دارو+آزمایش+context). خالی/نامعتبر → fallback امن به `get_patient_context`.

## ۱۰–۱۱) امنیت / ایزوله‌سازی / اسناد

- هر ابزار فقط `patient_id`/`limit` اسکالری می‌پذیرد — **بدون SQL/نام جدول/کلید ذخیره‌سازی** (تست اینتروسپکشن امضاها)
- `patient_id` **همیشه** از route اسکوپ‌شده تزریق می‌شود؛ مدل فقط نام ابزار می‌دهد
- ایزوله‌سازی بیمار تست‌شده (دادهٔ B از A دیده نمی‌شود؛ بیمار ناشناخته → ToolError تمیز)
- اسناد فقط **metadata** (۸ فیلد) — بدون storage_key/extracted_text/URL؛ فایل اصلی همچنان فقط از endpoint امن تسک ۶/۱۶

## ۱۲–۱۵) ارتباط با تسک‌ها

- **تسک ۹:** بازاستفادهٔ مستقیم (Context + Timeline) — بدون تغییر
- **تسک ۱۵:** endpoint گفتگوها دست‌نخورده و تست‌هایش سبز؛ Agent مسیر stateless جدا دارد و چیزی persist نمی‌کند
- **تسک ۱۶:** ادغام evidence در Agent **به تسک بعدی موکول شد** (نیازمند annotate ابزارها با evidence_id بود؛ ارزان نبود و ریسک خرابکاری داشت — طبق §13 مجاز)
- **تسک ۱۴/۱۱:** کاملاً دست‌نخورده؛ Rule Engine خارج از معماری Agent ماند

## ۱۶) تست‌ها — **271 passed** (+۲۷: ۱۲ MCP + ۱۵ Agent)

MCP: امضای ثابت فقط-خواندنی · ۶ ابزار با PG واقعی · limit/ترتیب · metadata-only اسناد · ایزوله‌سازی · بیمار ناشناخته · **stdio integration واقعی** (subprocess + initialize + tools/list + call با seed واقعی commit شده). Agent: انتخاب ابزار دارو/آزمایش/context/سند · multi-tool · حذف ابزار جعلی · پاسخ مستقیم · MCP down→503 · tool fail→502 بدون دادهٔ جعلی · Gemini fail→502 · بدون کلید→503 · planner خراب→502 · نتیجهٔ خالی · 404/422 · هم‌زیستی با چت معمولی و ماندگار. همهٔ LLM/MCP در unit تست‌ها mock؛ داده در تست‌های ابزار واقعی.

## ۱۷–۱۸) Smoke محلی و نتیجهٔ Gemini

- **MCP واقعاً زنده:** از طریق همان کلاینت تولیدی `MCPStdioClient` → subprocess واقعی → ۶ ابزار → دادهٔ واقعی: `['Losartan 50','Metformin 500']`، `HbA1c=8.2`، metadata اسناد، خطای تمیز بیمار ناشناخته ✓
- **Gemini واقعی: ❌** — هر ۳ سؤال → 502 تمیز (403 بلاک شبکهٔ Google؛ همان محدودیت مستند تسک‌های ۱۲–۱۶؛ بدون AI_PROXY). لاگ: `gemini planner call started` ×3 سپس `AIError: Google blocked…`. **Mock به‌عنوان smoke گزارش نمی‌شود** — مسیر موفق فقط با provider فرقی در تست‌ها پوشش داده شد.
- محیط: backend=8000 ✓، PostgreSQL/MinIO واقعی ✓، MCP محلی ✓، dev فرانت روی 3100 **نشد** (EACCES — پورت در محدودهٔ رزرو ویندوز)؛ روی پورت خودکار 13161 سرو شد و صفحهٔ بیماران 200 داد؛ تایید اصلی UI = production build ✓

## ۱۹) مشکلات / محدودیت‌ها

1. پاسخ موفق LLM روی این ماشین live نشد (بلاک شبکه).
2. انتخاب ابزار متنی (نه function-calling بومی) — احتمال خطای planner بیشتر؛ fallback امن داریم.
3. ابزارهای تخصصی Context کامل می‌سازند (کارایی) — نیاز به استخراج loader ها در پذیرش واقعی.
4. کلاینت MCP یک subprocess ماندگار + حلقهٔ async در thread پس‌زمینه است — برای spike ساده، ولی یعنی یک lifecycle جدید برای مدیریت.
5. SDK رسمی `mcp 2.2.0` + **۱۶ پکیج وابستهٔ transit** (cryptography، jsonschema، …) اضافه شد.

## ۲۰) Complexity اضافه‌شده (کد صادقانه)

~۷۰۰ خط جدید: `mcp_server.py` (~۲۰۰) · `agent.py` (~۲۵۰: نیمی فقط مدیریت subprocess/session) · route (~۹۰) · تست‌ها (~۴۰۰) · فرانت (~۶۰). + یک dependency با ۱۶ پکیج. + یک process جدید در runtime.

## ۲۱) آیا MCP ارزش ادامه دادن دارد؟ — **ارزیابی صادقانه: در این پروژه، فعلاً خیر**

- **چرا خیر (در MVP فعلی):** Context کامل از قبل کار می‌کند و سقف‌دار/بریده است؛ برای MVP دانشگاهی حجم Context مشکل واقعی نیست و evidence تسک ۱۶ grounding را می‌دهد. هزینه: subprocess + SDK + دو فراخوانی LLM در هر سؤال (کندتر و گران‌تر) + دیباگ سخت‌تر (سه لایه: planner/MCP/answerer در مقابل یک فراخوانی). امنیت: patient_id تزریقی خوب بود ولی قابل رسیدن با یک wrapper ساده هم بود.
- **کی بله می‌شود:** وقتی (الف) پرونده‌ها آن‌قدر بزرگ شوند که Context کامل گران/ناکافی باشد، (ب) تعداد ابزارها زیاد شود (اسناد per-سند، جستجو، دارو…) و انتخاب پویا ارزشمند شود، یا (ج) بخواهیم agent های خارجی (مثل Claude Desktop) به این پرونده وصل شوند — همان‌جا MCP استاندارد واقعیِ خودش است.
- جمع‌بندی: **spike هدفش را انجام داد** — مرزبندی و ایزوله‌سازی اثبات‌پذیر شد؛ ولی جایگزینی معماری چت فعلی توجیه پیدا نکرد. نگه داشتن به‌عنوان مسیر آزمایشی (`agent/chat` جدا) بدون دست زدن به چت اصلی، تصمیم درست است.

## ۲۲) چه چیزهایی می‌تواند ساده‌تر شود اگر ادامه دهد؟

استخراج loader های بخش‌ای از `patient_context.py` (ابزارها دیگر Context کامل نمی‌سازند) · agent loop تک‌فراخوانی با function-calling بومی Gemini (نیازمند توسعهٔ provider) · حذف نیازمندی به thread-bridge با async کردن کامل route ها.

## ۲۳) چه چیزهایی نباید با MCP جایگزین شود؟

همه‌چیز write-side و امنیتی: CRUD بالینی، آپلود/حذف، مکالمات ماندگار و evidence (تسک ۱۵/۱۶)، ایمنی نسخه قطعی (تسک ۱۴)، Rule Engine تسک ۱۱، دسترسی فایل/URL امضاشده. MCP فقط خواندنِ کنترل‌شده می‌ماند.

## ۲۴) فایل‌ها

**اضافه:** `app/mcp_server.py` · `app/services/agent.py` · `app/api/v1/routes/agent.py` · `tests/test_mcp_tools.py` · `tests/test_agent_api.py` · گزارش
**تغییر:** `requirements.txt` (+mcp) · `api.py` (ثبت روتیر) · فرانت: `types.ts`/`api.ts`/`clinical-chat.tsx` (حالت Agent) · READMEها
**(به‌علاوهٔ تغییرات uncommitted تسک ۱۶ که از قبل در working tree بود)**
**بدون migration.**
