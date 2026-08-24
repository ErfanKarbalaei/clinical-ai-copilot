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

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients` | Create a patient (201; 409 on duplicate national code) |
| GET | `/api/v1/patients` | List patients — `?q=` search (name/national code), `?limit=` (≤100), `&offset=` |
| GET | `/api/v1/patients/{id}` | Get a patient (404 if missing) |
| PATCH | `/api/v1/patients/{id}` | Partially update a patient |
| DELETE | `/api/v1/patients/{id}` | Delete a patient and all related clinical data (204) |

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
