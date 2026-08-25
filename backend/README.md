# Backend — Clinical AI Copilot

FastAPI service (Python 3.11+). Contains the project foundation (Task 1) and
the patient data model (Task 2): configuration, logging, database wiring,
ORM models, one Alembic migration, and the health endpoints. No clinical API
endpoints yet.

## Structure

```
backend/
├── app/
│   ├── core/        # configuration + logging
│   ├── db/          # engine/session + declarative Base + mixins
│   ├── models/      # ORM models (Patient, Condition, Medication, Document, ...)
│   ├── schemas/     # Pydantic schemas
│   ├── api/         # HTTP routers (v1)
│   ├── services/    # business services (empty — added in later tasks)
│   └── utils/       # shared helpers (empty — added in later tasks)
├── tests/           # pytest tests (health, models, seed)
├── alembic/         # migrations
├── scripts/         # development scripts (seed.py)
├── requirements.txt
├── requirements-dev.txt
├── alembic.ini
└── pytest.ini
```

## Setup

```bash
cd backend
python -m venv .venv

# Windows (Git Bash)
source .venv/Scripts/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements-dev.txt
```

Configuration is read from environment variables or a `.env` file. The
backend looks for `backend/.env` first and then the repository-root `.env`
(copy `.env.example` from the repo root to `.env`).

## Run (development)

```bash
uvicorn app.main:app --reload --port 8000
```

- API base: http://localhost:8000/api/v1
- Interactive docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health (also `/api/v1/health`)

### API endpoints

**Patients**

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients` | Create a patient (201; 409 on duplicate national code) |
| GET | `/api/v1/patients` | List patients — `?q=` search (name/national code), `?limit=` (≤100), `&offset=` |
| GET | `/api/v1/patients/{id}` | Get a patient (404 if missing) |
| PATCH | `/api/v1/patients/{id}` | Partially update a patient |
| DELETE | `/api/v1/patients/{id}` | Delete a patient and all related clinical data (204) |
| GET | `/api/v1/patients/{id}/overview` | Structured clinical overview (profile, conditions, active medications, allergies, 5 recent labs/notes) — no AI summary |

**Conditions** (active first, then newest onset first)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/conditions` | Add a condition (201) |
| GET | `/api/v1/patients/{id}/conditions` | List the patient's conditions |
| GET/PATCH/DELETE | `/api/v1/conditions/{id}` | Get / partially update / delete a condition |

**Allergies** (severe first)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/allergies` | Add an allergy (201) |
| GET | `/api/v1/patients/{id}/allergies` | List the patient's allergies |
| GET/PATCH/DELETE | `/api/v1/allergies/{id}` | Get / partially update / delete an allergy |

**Patient medications** (active → stopped → completed; newest start first; history preserved — stop via PATCH, not DELETE)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/medications` | Add a medication — by `medication_id` **or** `medication_name` (catalog entry is reused/created) |
| GET | `/api/v1/patients/{id}/medications` | List medications — `?status=active|stopped|completed` filter |
| GET/PATCH/DELETE | `/api/v1/patient-medications/{id}` | Get / partially update (dose, frequency, status, notes) / delete a record |

**Documents** (originals stored unchanged in MinIO; only metadata in PostgreSQL)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/documents` | Multipart upload — `file` + optional `title`, `doc_type` (201; PDF/PNG/JPEG/WebP/txt, max 20 MB; creates a `document_uploaded` timeline event) |
| GET | `/api/v1/patients/{id}/documents` | List a patient's documents (newest first) |
| GET | `/api/v1/documents/{id}` | Document metadata |
| GET | `/api/v1/documents/{id}/download` | 307 redirect to a 1-hour presigned URL served by MinIO |
| PATCH | `/api/v1/documents/{id}` | Update metadata (title/type) — the original file never changes |
| DELETE | `/api/v1/documents/{id}` | Delete the file from MinIO + metadata + timeline event (204) |

Storage errors return **503** (`سرویس ذخیره‌سازی فایل در دسترس نیست`).
Development E2E check: `python -m scripts.e2e_documents` (needs backend +
PostgreSQL + MinIO running).

Validation: `national_code` must be exactly 10 digits and unique;
`date_of_birth` must be in the past. Custom errors (404/409) return Persian
messages.

## Tests

```bash
python -m pytest
```

Health-endpoint tests always run. Model/seed tests need PostgreSQL and are
skipped automatically when it is not reachable (start it with
`docker compose up -d postgres`). They run against a separate
`<POSTGRES_DB>_test` database and never touch development data.

## Alembic (migrations)

Current head: `d3d54628e9bd` — *create core clinical entities* (10 tables).

```bash
alembic upgrade head      # apply migrations
alembic downgrade base    # revert all (drops tables + enum types)
alembic check             # verify models match the database
```

After changing models, generate a new migration:

```bash
alembic revision --autogenerate -m "message"
```

The database URL for Alembic comes from the same application settings —
never from `alembic.ini`.

## Seed data (development only)

```bash
python -m scripts.seed            # insert sample data (refuses if data exists)
python -m scripts.seed --reset    # wipe clinical tables and reseed
```

Inserts 3 fictional patients with conditions, medications, allergies,
documents, voice notes, notes, lab results, and timeline events.
