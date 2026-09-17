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
| GET | `/api/v1/patients/{id}/context` | **Complete patient context** — everything in the DB (demographics, conditions, full medication history, allergies, labs, documents incl. extracted text, voice notes incl. raw transcripts, notes). Input layer for the future AI copilot — pure structured data |
| GET | `/api/v1/patients/{id}/timeline` | **Unified clinical timeline** `{items, total}` — derived from actual records (documents, labs, notes, voice notes, condition onsets/resolutions, medication starts/stops), newest first, missing dates fall back to created_at |

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

**Voice notes** (Persian speech-to-text via Speechmatics; audio originals preserved in MinIO; raw transcript never auto-becomes a note)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/voice-notes` | Multipart audio upload (`file`, `title`, `conversation_type`, `duration_seconds`) — transcription runs automatically, then optional AI cleanup when a provider is configured (201; ≤50 MB) |
| GET | `/api/v1/patients/{id}/voice-notes` | List (newest first) |
| GET | `/api/v1/voice-notes/{id}` | Voice note + raw transcript + optional `cleaned_note`/`error_message`/`processed_at` |
| GET | `/api/v1/voice-notes/{id}/download` | 307 redirect to a presigned URL (original audio) |
| PATCH | `/api/v1/voice-notes/{id}` | Rename (title only) |
| POST | `/api/v1/voice-notes/{id}/transcribe` | Re-run transcription (202; 409 while running) |
| POST | `/api/v1/voice-notes/{id}/note` | Save the doctor-reviewed transcript as a clinical note (linked back to the recording) |
| DELETE | `/api/v1/voice-notes/{id}` | Delete audio + row + timeline event (derived notes are kept) |

Speech-to-Text: provider-agnostic layer — ready-to-use **Speechmatics batch
API** (`STT_PROVIDER=speechmatics`, `STT_LANGUAGE=fa`, `enhanced` operating
point). Doctor–patient conversations are transcribed with **speaker
diarization** (transcript keeps `S1:`/`S2:` turns); physician notes skip it.
Set `STT_API_KEY` in `.env` (or the legacy `SPEECHMATICS_API_KEY`) — without
a key, transcriptions deterministically end as `failed` with the reason
logged (`error_message`).

After a successful transcription, an **optional AI cleanup** (existing
Gemini provider) formats the raw transcript into a concise clinical note
(`cleaned_note`) — formatting/clarification only, never new medical
information; a Gemini failure leaves the raw transcript and the completed
status fully intact (`cleanup_status=failed`).

**Medication safety** (deterministic rule engine — warnings are NEVER generated by an LLM)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/medications/check` | Check a candidate (`medication_id` **or** `medication_name`, optional `dosage`) against the patient's active meds + allergies: drug–drug interactions, allergy conflicts, duplicate therapy. `explain=true` adds an optional Persian LLM *explanation* of the warnings (never new ones); provider outage leaves warnings intact |

**AI medication safety** (LLM decision support — independent of the rule engine above)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/medications/ai-safety-check` | AI-assisted analysis of 1–5 candidate medications (`name` + optional `dose`, optional `question`) against the patient's full Task-9 context via the existing Gemini provider. Grounded prompt: distinguishes potential vs well-established interactions, surfaces patient-specific factors, missing information and uncertainty; strict JSON contract — malformed model output never reaches the client (502). Nothing persisted; never blocks saving. `medication_safety: true` on `/chat` switches the chat to the same safety analysis |

**Persistent clinical conversations** (Task 15 — the stateless `/chat` endpoint above remains for compatibility)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/conversations` | Create a conversation (optional `title`; default «گفتگوی جدید», later derived deterministically from the first message) |
| GET | `/api/v1/patients/{id}/conversations` | List conversations, most recently updated first |
| GET | `/api/v1/conversations/{id}` | Conversation metadata + messages (oldest first) |
| POST | `/api/v1/conversations/{id}/messages` | Persisted exchange: saves the user message, builds the live Task-9 patient context + the last 20 messages as history, calls the existing AI provider (`medication_safety=true` → Task-14 safety prompt), persists the assistant answer, bumps `updated_at`. Provider failure → 502 with the user message kept for traceability, never a fabricated answer |
| DELETE | `/api/v1/conversations/{id}` | Delete the conversation and all its messages (cascade) |

Messages now carry **validated patient-record evidence** (Task 16): every
context item is tagged with a stable evidence id (`MED-42`, `ALLERGY-8`,
`COND-17`, `LAB-31`, `DOC-123`, `NOTE-45`, `VOICE-9`) sent to the model;
each assistant message stores only the ids the backend could validate
against that patient's real records. Document-backed evidence exposes
`document_id` — the ORIGINAL file is opened through the existing
`GET /documents/{id}/download` endpoint (307 → short-lived presigned URL);
the model never sees URLs and no URL is ever persisted.

**Clinical AI agent — MCP spike** (Task 17; separate from the chat above)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/agent/chat` | Stateless agent path: the existing AI provider picks 1–3 read-only tools (`get_patient`, `get_patient_context`, `get_patient_labs`, `get_patient_medications`, `get_patient_documents`, `get_patient_timeline`) executed through a LOCAL MCP server (`app/mcp_server.py`, official `mcp` SDK over stdio) that reuses the Task-9 builders against real PostgreSQL. `patient_id` is always injected server-side; documents are metadata-only. Answers are not persisted. Requires `pip install -r requirements.txt` (adds `mcp`) |

Warnings cite a `rule_id` from the versioned knowledge base
(`app/data/medication_rules.json`, ~30 drug classes with Persian/English
brand+generic aliases, 32 interactions, cross-reactivity rules;
`rules_version` returned with every check). The check is computed live —
no data duplication, no new tables.

**Clinical AI assistant** (decision support — no RAG, no vector search)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/chat` | `{question, history?}` → `{patient_id, question, answer, generated_at}`. The patient's full structured context (Task 9) + the question are sent to a ready-to-use model. 503 when unconfigured, 502 on provider failure |

Provider-agnostic — two implementations behind one interface, switched by
pure configuration (`AI_PROVIDER` in `.env`):

- **`gemini`** — native Google Gemini API (`generateContent`, v1beta);
  default model `gemini-3.6-flash`. Set `AI_API_KEY` to a Google AI Studio
  key.
- **`openai_compatible`** — any OpenAI-style `chat/completions` API
  (OpenAI, OpenRouter, local Ollama/vLLM/LM Studio via `AI_BASE_URL`);
  default model `gpt-4o-mini`.

Optional `AI_MODEL` overrides the provider default. Stateless — no chat
storage; the frontend keeps the visible transcript. Answers are grounded
in the patient's data only; the physician makes the final decision.

**Documents** (originals stored unchanged in MinIO; only metadata in PostgreSQL)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/patients/{id}/documents` | Multipart upload — `file` + optional `title`, `doc_type` (201; PDF/PNG/JPEG/WebP/txt, max 20 MB; creates a `document_uploaded` timeline event) |
| GET | `/api/v1/patients/{id}/documents` | List a patient's documents (newest first) |
| GET | `/api/v1/documents/{id}` | Document metadata |
| GET | `/api/v1/documents/{id}/download` | 307 redirect to a 1-hour presigned URL served by MinIO |
| PATCH | `/api/v1/documents/{id}` | Update metadata (title/type) — the original file never changes |
| DELETE | `/api/v1/documents/{id}` | Delete the file from MinIO + metadata + timeline event (204) |
| POST | `/api/v1/documents/{id}/extract` | Re-run text extraction (202; 409 while already processing) |
| POST | `/api/v1/documents/{id}/analyze` | **AI analysis** of the extracted text → Persian clinical summary (`ai_summary`, `analysis_status`); 409 if extraction not completed; 503/502 when the AI provider is unavailable |

**Text extraction** (deterministic — no AI): runs automatically after each
upload as a background task. `pending → processing → completed | failed`.
- `text/plain` → decoded directly
- PDFs → embedded text layer (pypdf); scans fall back to OCR over the
  page's embedded images
- images → Tesseract OCR (`fas+eng` when Persian data is installed)

OCR is optional — without the Tesseract binary, text PDFs still extract and
scans/images fail with a logged reason. Install options:
`choco install tesseract` (admin), `scoop install tesseract`, or set
`TESSERACT_CMD` in `.env` to the binary path (add `fas.traineddata` from
[tessdata](https://github.com/tesseract-ocr/tessdata) for Persian).

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
