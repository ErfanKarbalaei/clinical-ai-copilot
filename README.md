# Clinical AI Copilot

<div dir="rtl">

**دستیار هوشمند بالینی برای پزشکان**

</div>

A lightweight, web-based **clinical AI copilot for doctors**, built as a
Bachelor's final-year project by two students. This is an
**engineering-integration** project: it combines reliable, ready-to-use tools
and models (document processing, Speech-to-Text with good Persian support,
LLMs, trusted medical evidence, and rule-based medication safety) into one
coherent clinical workflow.

> **Important**
>
> - The system is **decision support only** — it does not replace a physician.
> - It does **not** autonomously diagnose or prescribe.
> - The **final decision always remains with the physician**.
> - AI output is never treated as the original source of truth.

## What this project is (and is not)

**Is:** an integration project — patient information + clinical documents +
voice documentation + ready-to-use AI models + trusted evidence + rule-based
safety checks, in one clinical workflow.

**Is not:** a model-training project. No new ML/OCR/STT/LLM models are trained
or fine-tuned. No RAG or vector database at this stage — retrieval starts
with SQL/metadata/full-text search and only escalates if evaluation proves it
necessary.

## Architecture overview

Monorepo with three main parts:

| Part | Stack | Role |
| --- | --- | --- |
| `backend/` | Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic | REST API (`/api/v1`), data access, integrations |
| `frontend/` | Next.js (App Router), TypeScript, TailwindCSS, shadcn/ui | Persian RTL web UI for physicians |
| `docker-compose.yml` | Docker Compose: PostgreSQL + MinIO | local data-layer infrastructure |

### Data architecture principles

- **Structured clinical data** (patient profile, conditions, medications,
  allergies, metadata, clinical events) → **PostgreSQL**
- **Original unstructured files** (PDFs, images, audio) → **MinIO**
  (S3-compatible object storage). Originals are preserved and never replaced.
- **Extracted text / transcripts** → PostgreSQL (useful for search and AI context)
- **Derived data** (summaries, AI answers, timeline representations) → stored
  for convenience, but **never the source of truth** — the original record
  always remains traceable.

## Repository structure

```
clinical-ai-copilot/
├── backend/                  # FastAPI service (Python 3.11+)
│   ├── app/
│   │   ├── core/             # configuration + logging
│   │   ├── db/               # engine/session + declarative Base + mixins
│   │   ├── models/           # ORM models (Patient, Condition, Medication, ...)
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── api/              # HTTP routers (v1)
│   │   ├── services/         # business services (empty — later tasks)
│   │   └── utils/            # shared helpers (empty — later tasks)
│   ├── tests/                # pytest tests
│   ├── alembic/              # migrations (initial clinical schema)
│   ├── scripts/              # dev scripts (seed.py)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── alembic.ini
│   └── pytest.ini
├── frontend/                 # Next.js app (Persian, RTL)
│   ├── src/
│   │   ├── app/              # App Router pages/layouts
│   │   ├── components/ui/    # shadcn/ui components (RTL-aware)
│   │   └── lib/
│   └── ...
├── infra/                    # reserved for future infra config
├── docs/                     # architecture & implementation documentation
├── .env.example              # environment variable template
├── .gitignore
├── docker-compose.yml        # PostgreSQL + MinIO
└── README.md
```

## Requirements

- Python **3.11+** (developed with 3.12)
- Node.js **20+** (LTS) and npm
- Docker + Docker Compose (for PostgreSQL and MinIO)
- Git

## Setup

```bash
git clone <repository-url>
cd clinical-ai-copilot
cp .env.example .env       # then edit values — never commit real credentials
```

## Docker (PostgreSQL + MinIO)

```bash
docker compose up -d       # start PostgreSQL + MinIO
docker compose ps          # check status / health
docker compose down        # stop (data volumes are kept)
docker compose down -v     # stop and delete all data
```

- PostgreSQL: `localhost:5432` (credentials from `.env`)
- MinIO API: `http://localhost:9000` — Console UI: `http://localhost:9001`

Only the data-layer services run in Docker. The backend and frontend run
locally during development.

## Backend

```bash
cd backend
python -m venv .venv

# Windows (Git Bash)          # Windows (PowerShell)      # Linux / macOS
source .venv/Scripts/activate # .venv\Scripts\Activate.ps1 # source .venv/bin/activate

pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

- API base: `http://localhost:8000/api/v1`
- Health: `http://localhost:8000/health` (also `/api/v1/health`) → `{"status": "ok"}`
- Interactive docs (Swagger): `http://localhost:8000/docs`

Tests:

```bash
cd backend
python -m pytest
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # adjust NEXT_PUBLIC_API_URL if needed
npm run dev
```

Open `http://localhost:3000` — the page is fully Persian and right-to-left
(RTL, Vazirmatn font, shadcn/ui with RTL support).

## Environment variables

Defined in `.env.example` (repo root — used by docker-compose and the
backend) and `frontend/.env.example` (used by Next.js):

| Variable | Used by | Description |
| --- | --- | --- |
| `POSTGRES_DB` | compose, backend | PostgreSQL database name |
| `POSTGRES_USER` | compose, backend | PostgreSQL user |
| `POSTGRES_PASSWORD` | compose, backend | PostgreSQL password |
| `POSTGRES_HOST` | backend | host the backend connects to |
| `POSTGRES_PORT` | compose, backend | PostgreSQL port (host + backend) |
| `MINIO_ENDPOINT` | backend, compose | MinIO endpoint, e.g. `localhost:9000` |
| `MINIO_ACCESS_KEY` | compose, backend | MinIO access key (root user) |
| `MINIO_SECRET_KEY` | compose, backend | MinIO secret key (root password) |
| `MINIO_BUCKET` | backend | bucket for clinical documents/audio |
| `MINIO_PORT` | compose | host port for the MinIO API |
| `MINIO_CONSOLE_PORT` | compose | host port for the MinIO console UI |
| `TESSERACT_CMD` | backend (optional) | absolute path to the Tesseract binary (empty = PATH lookup) |
| `BACKEND_PORT` | backend (reference) | backend port (default `8000`) |
| `NEXT_PUBLIC_API_URL` | frontend | public backend API base URL, inlined at build time |

The backend additionally supports an optional `CORS_ORIGINS` variable
(comma-separated browser origins; defaults to `http://localhost:3000`).

## Current development status

**Done — Task 1 (project foundation):**

- Monorepo layout (`backend/`, `frontend/`, `infra/`, `docs/`)
- Backend skeleton: FastAPI app, environment-based configuration (pydantic-settings),
  logging setup, SQLAlchemy engine/session wiring, empty Alembic setup,
  `GET /health` (root + `/api/v1/health`), pytest suite (3 tests, passing)
- Frontend skeleton: Next.js 16 App Router + TypeScript + TailwindCSS 4 +
  shadcn/ui (RTL), Persian RTL landing page with bundled Vazirmatn font
- Infrastructure: `docker-compose.yml` with PostgreSQL 17 + MinIO
  (persistent volumes, healthchecks, configurable credentials/ports)
- Environment template (`.env.example`) and documentation (READMEs)

**Done — Task 2 (patient data model):**

- 10 core entities: patients, conditions, medications, patient_medications,
  allergies, documents, voice_notes, clinical_notes, lab_results,
  clinical_events (see `docs/data-model/README.md`)
- Alembic migration `d3d54628e9bd` (create core clinical entities) — fully
  reversible, `alembic check` clean
- Database tests (13 passing): defaults, unique national code, FK
  cascades, voice-note/document traceability links
- Development seed script (`backend/scripts/seed.py`) with sample Persian
  clinical data
- Documentation: data-model reference + Task 2 report

**Done — Task 3 (patient API):**

- Patient CRUD endpoints under `/api/v1/patients`: create, list (search +
  pagination), get, partial update, delete (cascades related clinical data)
- Persian error messages for 404/409; validation (کد ملی = 10 unique digits,
  past date of birth)
- 14 new API tests — full suite: 27 passing
- See `backend/README.md` for the endpoint table

**Done — Task 4 (clinical APIs):**

- Conditions API: nested create/list + flat get/patch/delete
  (`/api/v1/patients/{id}/conditions`, `/api/v1/conditions/{id}`)
- Allergies API: same shape (`/api/v1/patients/{id}/allergies`,
  `/api/v1/allergies/{id}`) — severe-first ordering
- Patient medications API (`/api/v1/patients/{id}/medications`,
  `/api/v1/patient-medications/{id}`) — by catalog id or name (catalog entry
  reused/created), active-first deterministic ordering, `?status=` filter,
  stopping preserves history
- Patient overview: `GET /api/v1/patients/{id}/overview` — profile,
  conditions, active medications, allergies, 5 recent labs/notes (pure
  structured data, no AI summary)
- 36 new API tests — full suite: 63 passing

**Done — Task 5 (frontend — patients & clinical record):**

- Persian RTL pages: `/` (landing → patients), `/patients` (server-rendered
  list with search + pagination + create dialog), `/patients/[id]` (clinical
  record: profile, conditions, allergies, active medications with
  add/edit/stop/delete, 5 recent labs, 5 recent notes)
- Typed API client (`lib/api.ts`) + Persian labels/Jalali dates (`lib/format.ts`)
- shadcn/ui components (dialog, input, label, select, textarea, table, ...)
- All data from the real API — no mock data; `tsc` + `next build` clean;
  SSR pages verified against the seeded backend

**Done — Task 6 (patient documents):**

- MinIO storage service (`services/storage.py`): bucket bootstrap, unique
  sanitized object keys (`patients/{id}/documents/{uuid}-{name}`), upload,
  presigned URLs, delete
- Documents API: multipart upload (PDF/PNG/JPEG/WebP/txt, ≤20 MB, Persian
  422s), list (newest first), metadata get/patch, download via 307
  presigned redirect, delete (file + metadata + timeline event); 503 when
  storage is down
- Upload/delete maintain the patient timeline automatically
- 17 new tests (API with faked storage + live-MinIO integration, auto-skip)
  — full suite: 80 passing; live E2E verified byte-identical roundtrip

**Done — Task 7 (document text extraction):**

- Deterministic extraction pipeline (no AI/LLM): text/plain decoded, PDFs
  via pypdf text layer with OCR fallback over embedded page images, images
  via Tesseract (`fas+eng`, optional — auto-detected)
- Runs as a FastAPI background task after upload: `pending → processing →
  completed | failed`; re-extract endpoint (`POST /documents/{id}/extract`)
- Race-safe processing (document deleted mid-extraction is handled) and
  storage-level `get_object_bytes`
- Frontend: documents section on the patient record — upload dialog, status
  badges (در انتظار/در حال پردازش/استخراج شد/ناموفق), download of the
  original, extracted-text viewer, re-extract on failure, delete
- 12 new tests (incl. live Persian OCR) — full suite: 92 passing; real-file
  E2E verified (text PDF, Persian image OCR, scanned PDF, byte-identical
  original, re-extract)

**Not started (intentionally — later phases):** authentication,
voice notes, Speech-to-Text, AI model integrations, medical-evidence
retrieval, prescription-safety rules, RAG/vector search.
