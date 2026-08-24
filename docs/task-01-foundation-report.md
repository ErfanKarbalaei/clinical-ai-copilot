# گزارش تسک ۱ — پی‌ریزی پروژه (Project Foundation)

- **پروژه:** Clinical AI Copilot — دستیار هوشمند بالینی برای پزشکان
- **تسک:** تسک ۱ (Task 1) — راه‌اندازی پایه پروژه (monorepo، بک‌اند، فرانت‌اند، زیرساخت، محیط، تست، مستندات)
- **تاریخ اجرا:** 2026-08-24
- **وضعیت:** ✅ تکمیل‌شده و راستی‌آزمایی‌شده
- **کامیت:** هنوز کامیت نشده است (فایل‌ها آمادهٔ کامیت هستند)

---

## ۱) دامنهٔ کار

طبق دستور تسک، **فقط** موارد زیر انجام شد و هیچ قابلیت تجاری/بالینی‌ای اضافه نشد:

- ساخت ساختار monorepo (پوشه‌های `backend` ، `frontend` ، `infra` ، `docs`)
- بک‌اند مینیمال با FastAPI (تنظیمات محیطی، لاگینگ، اتصال SQLAlchemy بدون مدل تجاری، تنظیم Alembic بدون مایگریشن، `GET /health` با پیشوند `/api/v1`)
- فرانت‌اند مینیمال با Next.js + TypeScript + TailwindCSS + shadcn/ui (صفحهٔ فرود فارسی و RTL)
- زیرساخت Docker Compose شامل فقط PostgreSQL و MinIO (بدون Redis ، Kafka ، Vector DB و...)
- فایل `.env.example` با متغیرهای محیطی مورد نیاز (بدون هیچ مقدار واقعی/محرمانه)
- راه‌اندازی pytest به‌همراه تست health endpoint
- مستندات (README ریشه، README بک‌اند، README فرانت‌اند، README داکیومنت‌ها و infra)

**مواردی که عمداً انجام نشد (فازهای بعدی):** احراز هویت، مدل دادهٔ بیمار، قابلیت‌های بالینی، پردازش اسناد، OCR، تبدیل گفتار به متن (STT)، یکپارچه‌سازی مدل‌های هوش مصنوعی، بازیابی شواهد پزشکی، ایمنی نسخه، RAG.

---

## ۲) ساختار نهایی مخزن (Directory Tree)

```
clinical-ai-copilot/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── backend/
│   ├── README.md
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/.gitkeep          # فعلاً هیچ مایگریشنی وجود ندارد
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # ساخت اپلیکیشن FastAPI
│   │   ├── core/
│   │   │   ├── config.py              # تنظیمات مبتنی بر محیط (pydantic-settings)
│   │   │   └── logging.py             # پیکربندی لاگینگ
│   │   ├── db/
│   │   │   ├── base.py                # DeclarativeBase (بدون مدل تجاری)
│   │   │   └── session.py             # engine + SessionLocal + get_db
│   │   ├── models/                    # خالی — تسک‌های بعدی
│   │   ├── schemas/
│   │   │   └── health.py              # HealthResponse
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── api.py             # روتیر تجمیعی v1
│   │   │       └── routes/health.py   # GET /api/v1/health
│   │   ├── services/                  # خالی — تسک‌های بعدی
│   │   └── utils/                     # خالی — تسک‌های بعدی
│   └── tests/
│       ├── conftest.py
│       └── test_health.py             # ۳ تست
├── frontend/
│   ├── .env.example                   # NEXT_PUBLIC_API_URL
│   ├── .env.local                     # مقدار توسعه (gitignore شده)
│   ├── .gitignore
│   ├── AGENTS.md / CLAUDE.md          # تولیدشده خودکار توسط Next.js (نگه داشته شد)
│   ├── README.md
│   ├── components.json                # shadcn با rtl: true
│   ├── eslint.config.mjs
│   ├── next.config.ts
│   ├── package.json / package-lock.json
│   ├── postcss.config.mjs
│   ├── tsconfig.json
│   ├── public/.gitkeep
│   └── src/
│       ├── app/
│       │   ├── favicon.ico
│       │   ├── globals.css            # تم shadcn + فونت Vazirmatn
│       │   ├── layout.tsx             # lang="fa" dir="rtl" + DirectionProvider
│       │   └── page.tsx               # صفحهٔ فرود فارسی RTL
│       ├── components/ui/             # button, card, badge, direction
│       └── lib/utils.ts
├── infra/
│   └── README.md
└── docs/
    ├── README.md
    └── task-01-foundation-report.md   # همین فایل
```

---

## ۳) فایل‌های ایجادشده

### ریشهٔ مخزن
| فایل | توضیح |
| --- | --- |
| `.env.example` | قالب متغیرهای محیطی (PostgreSQL ، MinIO ، پورت‌ها، آدرس API) — بدون مقدار واقعی |
| `.gitignore` | پوشش Python ، Node/Next ، فایل‌های env ، IDE ، OS |
| `docker-compose.yml` | PostgreSQL 17-alpine + MinIO با volume مانا، healthcheck و پورت/اعتبارنامهٔ قابل‌تنظیم |
| `README.md` | معرفی پروژه، معماری، ساختار، راهنمای اجرا، متغیرهای محیطی، وضعیت توسعه |

### بک‌اند (۲۰ فایل)
`app/main.py`، `app/core/{config,logging}.py`، `app/db/{base,session}.py`، `app/schemas/health.py`، `app/api/v1/api.py`، `app/api/v1/routes/health.py`، ۹ فایل `__init__.py` (پکیج‌ها)، `alembic/env.py`، `alembic/script.py.mako`، `tests/{conftest,test_health}.py`، `requirements.txt`، `requirements-dev.txt`، `pytest.ini`، `alembic.ini`، `README.md`

### فرانت‌اند
سکلتی با `create-next-app@latest` + شخصی‌سازی:
- `src/app/layout.tsx` — بازنویسی‌شده: `lang="fa"` ، `dir="rtl"` ، `DirectionProvider` (Base UI) با `direction="rtl"` و فونت Vazirmatn
- `src/app/page.tsx` — صفحهٔ فرود فارسی RTL با shadcn (Card ، Badge ، Button)
- `src/app/globals.css` — تم shadcn + تعریف استک فونت `--font-sans: "Vazirmatn", ...`
- کامپوننت‌های shadcn: `button` ، `card` ، `badge` ، `direction`
- `.env.example` و `.env.local` (مقدار `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`)
- اصلاح `.gitignore` فرانت‌اند برای کامیت‌شدن `.env.example`
- حذف تصاویر SVG پیش‌فرض استفاده‌نشده از `public/`

### مستندات و زیرساخت
`docs/README.md`، `infra/README.md`، `backend/README.md`، بازنویسی `frontend/README.md`، همین گزارش.

---

## ۴) تصمیم‌های فنی مهم

1. **Health endpoint در دو مسیر:** هم `GET /health` (مسیر پایدار برای probeهای زیرساختی، مطابق متن تسک) و هم `GET /api/v1/health` (بخشی از سطح API نسخه‌دار). هر دو دقیقاً `{"status": "ok"` برمی‌گردانند.
2. **تنظیمات:** با `pydantic-settings`؛ فایل `.env` از `backend/.env` و سپس `.env` ریشهٔ مخزن خوانده می‌شود تا یک فایل ریشه برای compose و بک‌اند کافی باشد.
3. **Alembic:** URL دیتابیس در `alembic/env.py` از تنظیمات همان اپلیکیشن تزریق می‌شود؛ `alembic.ini` هرگز حاوی اعتبارنامهٔ واقعی نیست. `target_metadata` به `Base.metadata` متصل است تا autogenerate در فازهای بعدی کار کند.
4. **CORS:** میان‌افزار CORS با پیش‌فرض `http://localhost:3000` (قابل‌ تغییر با متغیر اختیاری `CORS_ORIGINS`) — چون فرانت‌اند روی پورت ۳۰۰۰ به بک‌اند روی ۸۰۰۰ درخواست می‌فرستد.
5. **RTL فرانت‌اند:** `dir="rtl"` روی `<html>` + `DirectionProvider` شادسن + مقدار `"rtl": true` در `components.json` (پرچم `--rtl` هنگام `shadcn init`).
6. **فونت فارسی:** پکیج npm ان `vazirmatn` (فونت متغیر، یک فایل woff2 حدود ۱۰۸KB) — بدون وابستگی به CDN فونت (مثل Google Fonts) و بدون مشکل شبکه هنگام build.
7. **Python:** venv با **Python 3.12** ساخته شد (پایتون پیش‌فرض سیستم 3.14 است؛ 3.12 سازگاری بهتری با `psycopg2-binary` دارد). الزام «3.11+» رعایت شده است.
8. **Next.js 16 / Tailwind 4 / shadcn v4 (پیش‌فرض base-nova با Base UI):** جدیدترین نسخه‌های پایدار؛ کامپوننت‌ها به‌جای `asChild` از پراپ `render` استفاده می‌کنند.

---

## ۵) نسخه‌های نصب‌شده

| بخش | مورد | نسخه |
| --- | --- | --- |
| سیستم | Node.js / npm | v24.18.0 / 11.4.1 |
| سیستم | Docker / Compose | 27.3.1 / v2.30.3 |
| بک‌اند | Python (داخل venv) | 3.12.2 |
| بک‌اند | FastAPI / Uvicorn | 0.141.1 / 0.52.4 |
| بک‌اند | Pydantic / pydantic-settings | 2.13.4 / 2.15.0 |
| بک‌اند | SQLAlchemy / Alembic / psycopg2-binary | 2.0.52 / 1.19.1 / 2.9.12 |
| بک‌اند | pytest / httpx | 8.4.2 / 0.28.1 |
| فرانت‌اند | Next.js / React | 16.3.2 / 19.2.8 |
| فرانت‌اند | TailwindCSS / shadcn CLI | 4.3.3 / 4.19.0 |
| فرانت‌اند | @base-ui/react / vazirmatn | 1.7.0 / 33.0.3 |

---

## ۶) دستورات اجراشده (خلاصه)

```bash
# --- بک‌اند ---
cd backend
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest                                    # ۳ تست
.venv/Scripts/python.exe -c "from app.main import app"                # بررسی import
.venv/Scripts/python.exe -m alembic history                           # بارگذاری Alembic
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000          # اجرای سرور
curl http://127.0.0.1:8000/health        # {"status":"ok"} + HTTP 200
curl http://127.0.0.1:8000/api/v1/health # {"status":"ok"} + HTTP 200
curl http://127.0.0.1:8000/docs          # HTTP 200

# --- فرانت‌اند ---
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
cd frontend
npm install vazirmatn
npx shadcn@latest init --yes --rtl --defaults
npx shadcn@latest add direction card badge --yes
npm run build        # موفق
npm run start        # اجرای سرور پروداکشن روی پورت ۳۰۰۰
curl http://127.0.0.1:3000/             # HTTP 200 + HTML فارسی RTL

# --- زیرساخت ---
docker compose config --quiet           # پیکربندی معتبر
docker compose config --services        # postgres, minio
```

---

## ۷) نتایج راستی‌آزمایی (Task 1H)

| # | مورد موردانتظار | نتیجه |
| --- | --- | --- |
| ۱ | نصب وابستگی‌ها | ✅ بک‌اند و فرانت‌اند بدون خطا |
| ۲ | اعتبار importهای پایتون | ✅ `from app.main import app` موفق |
| ۳ | تست‌های بک‌اند | ✅ **3 passed** در `0.04s` |
| ۴ | اجرای بک‌اند (uvicorn) | ✅ اجرا شد روی پورت ۸۰۰۰ |
| ۵ | `GET /health` | ✅ HTTP 200 با `{"status": "ok"}` (هر دو مسیر `/health` و `/api/v1/health`) |
| ۶ | اجرای فرانت‌اند (`next build` + `next start`) | ✅ بیلد موفق (TypeScript OK، صفحهٔ استاتیک تولید شد) و سرور اجرا شد |
| ۷ | رندر صفحهٔ فرانت‌اند | ✅ HTTP 200؛ `<html lang="fa" dir="rtl">`؛ متن «محیط توسعه پروژه با موفقیت اجرا شده است.» و «دستیار هوشمند بالینی برای پزشکان» در HTML خروجی |
| ۸ | فونت فارسی | ✅ فایل `Vazirmatn[wght].woff2` با HTTP 200 و `font/woff2` سرو شد (۱۱۱٬۱۵۲ بایت) |
| ۹ | اتصال متغیر محیطی | ✅ مقدار `NEXT_PUBLIC_API_URL` در صفحهٔ رندرشده ظاهر شد |
| ۱۰ | اعتبار `docker-compose.yml` | ✅ `docker compose config` بدون خطا (سرویس‌ها: postgres ، minio) |
| ۱۱ | عدم وجود قابلیت تجاری ناخواسته | ✅ `models/` ، `services/` ، `utils/` فقط docstring دارند؛ هیچ مایگریشن/مدل بالینی وجود ندارد |
| ۱۲ | RTL بودن پیش‌فرض فرانت‌اند | ✅ `dir="rtl"` + `DirectionProvider` + `"rtl": true` در `components.json` |

---

## ۸) هشدارها و نکات (بدون مانع)

1. **هشدار deprecation در تست‌ها:** Starlette پیام اطلاعاتی می‌دهد که `httpx` در TestClient منسوخ شده و پیشنهاد `httpx2` دارد. صرفاً اطلاع‌رسانی است؛ تست‌ها بدون مشکل پاس می‌شوند. در فاز بعدی می‌توان به `httpx2` مهاجرت کرد.
2. **هشدار npm هنگام نصب:** `eslint@9.39.5 is deprecated` — مربوط به وابستگی‌های پیش‌فرض `create-next-app` است و روی اجرای پروژه اثری ندارد.
3. **Telemetry در Next.js:** هنگام build پیام telemetry نمایش داده می‌شود؛ با `npx next telemetry off` قابل غیرفعال‌سازی است.
4. **فایل‌های `AGENTS.md` و `CLAUDE.md` در فرانت‌اند:** به‌صورت خودکار توسط Next.js 16 تولید و مدیریت می‌شوند (حذفشان باعث بازتولید می‌شود)؛ عمداً دست‌نخورده باقی ماندند.
5. **`NEXT_PUBLIC_API_URL` هنگام build اینلاین می‌شود:** اگر مقدار آن تغییر کند، فرانت‌اند باید دوباره build/ری‌استارت شود.
6. **`.env.local` فرانت‌اند و `.env` ریشه gitignore هستند:** فقط نسخه‌های `.env.example` کامیت می‌شوند — عمدی و مطابق اصل «بدون secret واقعی در مخزن».
7. **کانتینرهای PostgreSQL و MinIO هنوز اجرا نشده‌اند:** زیرساخت فقط اعتبارسنجی شد (`docker compose config`)، چون در این مرحله هیچ کدی به دیتابیس/شیءاستوریج وصل نیست. اولین اجرای واقعی در فاز مدل داده انجام می‌شود.
8. **هنوز کامیت نشده است:** تمام فایل‌ها untracked هستند و آمادهٔ کامیت‌اند.

---

## ۹) نحوهٔ اجرای پروژه

```bash
# 0) متغیرهای محیطی
cp .env.example .env                    # ریشهٔ مخزن

# 1) زیرساخت داده (اختیاری در این مرحله)
docker compose up -d                    # PostgreSQL + MinIO

# 2) بک‌اند
cd backend
python -m venv .venv
source .venv/Scripts/activate           # ویندوز Git Bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs  |  /health

# 3) فرانت‌اند (در ترمینال جدید)
cd frontend
npm install
cp .env.example .env.local
npm run dev
# → http://localhost:3000 (فارسی، RTL)

# 4) تست‌های بک‌اند
cd backend && python -m pytest
```

---

## ۱۰) گام بعدی

طبق دستورالعمل توسعهٔ پروژه، پس از تسک ۱ **متوقف می‌شویم** و منتظر دستور بعدی هستیم.
گام منطقی بعدی (پس از تأیید): طراحی مدل دادهٔ بیمار و ایجاد اولین مایگریشن‌های Alembic.
