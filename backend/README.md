# Backend — Clinical AI Copilot

FastAPI service (Python 3.11+). Currently contains **only the project
foundation**: environment-based configuration, logging, database
engine/session wiring, an empty Alembic setup, and the health endpoints.
No business features yet.

## Structure

```
backend/
├── app/
│   ├── core/        # configuration + logging
│   ├── db/          # SQLAlchemy engine/session + declarative Base
│   ├── models/      # ORM models (empty — added in later tasks)
│   ├── schemas/     # Pydantic schemas
│   ├── api/         # HTTP routers (v1)
│   ├── services/    # business services (empty — added in later tasks)
│   └── utils/       # shared helpers (empty — added in later tasks)
├── tests/           # pytest tests
├── alembic/         # migrations (no migrations yet)
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

## Tests

```bash
python -m pytest
```

## Alembic (migrations)

No migrations exist yet (no business models). Once models are added:

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

The database URL for Alembic comes from the same application settings —
never from `alembic.ini`.
