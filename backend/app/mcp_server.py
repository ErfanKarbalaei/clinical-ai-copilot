"""Local read-only MCP server for the Clinical AI Copilot (Task 17 spike).

Bridges an AI agent to the EXISTING data layer — every tool reuses the
Task-9 patient context / timeline builders and the real models, connects
to the same PostgreSQL, and returns REAL patient data. No mock data, no
duplicate query logic, no write operations of any kind.

Security posture:
- tools accept ONLY declared scalar parameters (patient_id, optional
  limit) — no arbitrary SQL, table names, file paths, or object keys
- every tool is patient-scoped by construction (all reused queries filter
  by patient_id); one call can never return another patient's data
- documents are exposed as METADATA ONLY — no storage keys, no
  extracted text, no presigned URLs (the original file stays behind the
  existing secure backend endpoint, Task 6/16)

Layout: ``_*_impl(db, ...)`` functions carry the logic and take an
injectable session (tests use the isolated test-session); the public
tools below are thin wrappers that open their own SessionLocal — the MCP
server is a separate process from the web app.

Run locally over stdio:  python -m app.mcp_server
"""

import logging
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Patient
from app.schemas.patient import PatientResponse
from app.services.patient_context import build_patient_context, build_timeline

logger = logging.getLogger(__name__)

# Document metadata safe for the agent — explicitly excludes storage_key,
# extracted_text and ai_summary (patient text stays out of tool metadata;
# the original file is only reachable via the existing backend endpoint).
_DOCUMENT_METADATA_FIELDS = (
    "id",
    "title",
    "doc_type",
    "file_name",
    "mime_type",
    "file_size_bytes",
    "extraction_status",
    "created_at",
)


class PatientNotFoundError(ToolError):
    """Unknown patient — surfaces to the client as a clean tool error."""


def _load_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise PatientNotFoundError(f"patient {patient_id} not found")
    return patient


# --- injectable implementations (used directly by the tests) ---


def _get_patient_impl(db: Session, patient_id: int) -> dict[str, Any]:
    return PatientResponse.model_validate(_load_patient(db, patient_id)).model_dump(
        mode="json"
    )


def _get_patient_context_impl(db: Session, patient_id: int) -> dict[str, Any]:
    context = build_patient_context(db, _load_patient(db, patient_id))
    return context.model_dump(mode="json")


def _get_patient_labs_impl(
    db: Session, patient_id: int, limit: int = 10
) -> list[dict[str, Any]]:
    context = build_patient_context(db, _load_patient(db, patient_id))
    return [lab.model_dump(mode="json") for lab in context.lab_results[:limit]]


def _get_patient_medications_impl(
    db: Session, patient_id: int
) -> list[dict[str, Any]]:
    context = build_patient_context(db, _load_patient(db, patient_id))
    return [med.model_dump(mode="json") for med in context.medications]


def _get_patient_documents_impl(
    db: Session, patient_id: int
) -> list[dict[str, Any]]:
    context = build_patient_context(db, _load_patient(db, patient_id))
    documents: list[dict[str, Any]] = []
    for document in context.documents:
        data = document.model_dump(mode="json")
        documents.append({field: data[field] for field in _DOCUMENT_METADATA_FIELDS})
    return documents


def _get_patient_timeline_impl(
    db: Session, patient_id: int, limit: int = 30
) -> dict[str, Any]:
    patient = _load_patient(db, patient_id)
    items = build_timeline(db, patient)
    return {
        "total": len(items),
        "items": [item.model_dump(mode="json") for item in items[:limit]],
    }


# --- public MCP tools (own session per call; fixed scalar signatures) ---


def get_patient(patient_id: int) -> dict[str, Any]:
    """Profile (demographics) of one patient — real DB row."""
    with SessionLocal() as db:
        return _get_patient_impl(db, patient_id)


def get_patient_context(patient_id: int) -> dict[str, Any]:
    """Full structured patient context (Task 9) — live from PostgreSQL."""
    with SessionLocal() as db:
        return _get_patient_context_impl(db, patient_id)


def get_patient_labs(patient_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Most recent lab results of one patient (newest first)."""
    with SessionLocal() as db:
        return _get_patient_labs_impl(db, patient_id, limit)


def get_patient_medications(patient_id: int) -> list[dict[str, Any]]:
    """Medication history of one patient — active first (Task 9 ordering)."""
    with SessionLocal() as db:
        return _get_patient_medications_impl(db, patient_id)


def get_patient_documents(patient_id: int) -> list[dict[str, Any]]:
    """Documents of one patient — METADATA ONLY (no storage keys/URLs/text)."""
    with SessionLocal() as db:
        return _get_patient_documents_impl(db, patient_id)


def get_patient_timeline(patient_id: int, limit: int = 30) -> dict[str, Any]:
    """Unified clinical timeline of one patient (Task 9), newest first."""
    with SessionLocal() as db:
        return _get_patient_timeline_impl(db, patient_id, limit)


server = MCPServer("clinical-copilot-mcp", version="0.1.0")

server.add_tool(get_patient, name="get_patient")
server.add_tool(get_patient_context, name="get_patient_context")
server.add_tool(get_patient_labs, name="get_patient_labs")
server.add_tool(get_patient_medications, name="get_patient_medications")
server.add_tool(get_patient_documents, name="get_patient_documents")
server.add_tool(get_patient_timeline, name="get_patient_timeline")

# Fixed tool surface — asserted by tests: only declared scalar parameters.
TOOL_NAMES = (
    "get_patient",
    "get_patient_context",
    "get_patient_labs",
    "get_patient_medications",
    "get_patient_documents",
    "get_patient_timeline",
)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    server.run("stdio")


if __name__ == "__main__":
    main()
