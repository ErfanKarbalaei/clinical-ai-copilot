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
│   │   ├── db/               # SQLAlchemy engine/session + declarative Base
│   │   ├── models/           # ORM models (empty — later tasks)
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── api/              # HTTP routers (v1)
│   │   ├── services/         # business services (empty — later tasks)
│   │   └── utils/            # shared helpers (empty — later tasks)
│   ├── tests/                # pytest tests
│   ├── alembic/              # migrations (no migrations yet)
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
| `MINIO_ENDPOINT` | backend (later) | MinIO endpoint, e.g. `localhost:9000` |
| `MINIO_ACCESS_KEY` | compose, backend (later) | MinIO access key (root user) |
| `MINIO_SECRET_KEY` | compose, backend (later) | MinIO secret key (root password) |
| `MINIO_BUCKET` | backend (later) | bucket for clinical documents/audio |
| `MINIO_PORT` | compose | host port for the MinIO API |
| `MINIO_CONSOLE_PORT` | compose | host port for the MinIO console UI |
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

**Not started (intentionally — later phases):** authentication, patient data
model and migrations, clinical features, document upload/processing, OCR,
Speech-to-Text, AI model integrations, medical-evidence retrieval,
prescription-safety rules, RAG/vector search.
