"""MCP tool tests — real PostgreSQL data, no mocks in the data path."""

import asyncio
import os
import sys

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.mcp_server import (
    TOOL_NAMES,
    get_patient,
    get_patient_context,
    get_patient_documents,
    get_patient_labs,
    get_patient_medications,
    get_patient_timeline,
)
from app.mcp_server import (
    _get_patient_impl,
    _get_patient_context_impl,
    _get_patient_documents_impl,
    _get_patient_labs_impl,
    _get_patient_medications_impl,
    _get_patient_timeline_impl,
)

PATIENTS_URL = "/api/v1/patients"


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL,
            json={"first_name": "آزمون", "last_name": f"MCP {suffix}"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def _seed(api_client, patient_id: int) -> None:
    api_client.post(
        f"{PATIENTS_URL}/{patient_id}/medications",
        json={"medication_name": "Metformin 500", "dosage": "500 mg"},
    )
    api_client.post(
        f"{PATIENTS_URL}/{patient_id}/conditions", json={"name": "دیابت نوع ۲"}
    )


# --- tool surface (security: fixed, read-only, no SQL/keys) ---


def test_tool_surface_is_fixed_and_read_only():
    assert sorted(TOOL_NAMES) == [
        "get_patient",
        "get_patient_context",
        "get_patient_documents",
        "get_patient_labs",
        "get_patient_medications",
        "get_patient_timeline",
    ]
    assert not any(
        word in name for name in TOOL_NAMES
        for word in ("create", "update", "delete", "write")
    )
    # signatures: only declared scalar params — no sql/key/path params
    import inspect

    for name in TOOL_NAMES:
        function = dict(inspect.getmembers(sys.modules["app.mcp_server"]))[name]
        params = inspect.signature(function).parameters
        assert set(params) <= {"patient_id", "limit"}, (name, list(params))


# --- direct tool calls against real PostgreSQL ---


def test_get_patient_returns_real_profile(api_client, db_session, make_patient):
    patient = make_patient("۱")
    profile = _get_patient_impl(db_session, patient["id"])
    assert profile["id"] == patient["id"]
    assert profile["first_name"] == "آزمون"


def test_get_patient_context_reuses_task9(api_client, db_session, make_patient):
    patient = make_patient("۲")
    _seed(api_client, patient["id"])
    context = _get_patient_context_impl(db_session, patient["id"])
    assert context["patient"]["id"] == patient["id"]
    assert any("Metformin" in med["medication"]["name"] for med in context["medications"])
    assert any(c["name"] == "دیابت نوع ۲" for c in context["conditions"])


def test_get_patient_labs_scoped_and_limited(api_client, db_session, make_patient):
    from app.models import LabResult

    a, b = make_patient("۳"), make_patient("۴")
    for i in range(3):
        db_session.add(
            LabResult(
                patient_id=a["id"], test_name=f"HbA1c-{i}", value="8", unit="%"
            )
        )
    db_session.add(LabResult(patient_id=b["id"], test_name="ALT", value="30"))
    db_session.commit()

    labs = _get_patient_labs_impl(db_session, a["id"], limit=2)
    assert len(labs) == 2  # limit honored
    assert all(lab["test_name"].startswith("HbA1c") for lab in labs)  # scoped to A


def test_get_patient_medications(api_client, db_session, make_patient):
    patient = make_patient("۵")
    _seed(api_client, patient["id"])
    medications = _get_patient_medications_impl(db_session, patient["id"])
    assert medications and medications[0]["medication"]["name"] == "Metformin 500"


def test_get_patient_documents_metadata_only(api_client, db_session, make_patient):
    from app.models import Document
    from app.models.enums import DocumentType

    patient = make_patient("۶")
    db_session.add(
        Document(
            patient_id=patient["id"],
            title="آزمایش خون",
            storage_key="patients/1/documents/secret-key.pdf",  # must NOT leak
            file_name="lab.pdf",
            mime_type="application/pdf",
            file_size_bytes=10,
            doc_type=DocumentType.lab_report,
        )
    )
    db_session.commit()

    documents = _get_patient_documents_impl(db_session, patient["id"])
    assert documents and documents[0]["title"] == "آزمایش خون"
    # document security: no storage key, no extracted text, no URLs
    assert set(documents[0]) == {
        "id",
        "title",
        "doc_type",
        "file_name",
        "mime_type",
        "file_size_bytes",
        "extraction_status",
        "created_at",
    }


def test_get_patient_timeline(api_client, db_session, make_patient):
    patient = make_patient("۷")
    _seed(api_client, patient["id"])
    timeline = _get_patient_timeline_impl(db_session, patient["id"])
    assert timeline["total"] >= 1
    assert timeline["items"][0]["source_type"] in {
        "condition", "patient_medication",
    }


def test_unknown_patient_errors_every_tool(db_session):
    from mcp.server.mcpserver.exceptions import ToolError

    for tool in (
        _get_patient_impl,
        _get_patient_context_impl,
        _get_patient_labs_impl,
        _get_patient_medications_impl,
        _get_patient_documents_impl,
        _get_patient_timeline_impl,
    ):
        with pytest.raises(ToolError):
            tool(db_session, 987654)


def test_patient_isolation_between_patients(api_client, db_session, make_patient):
    a, b = make_patient("۸"), make_patient("۹")
    _seed(api_client, b["id"])  # data only on B

    assert _get_patient_medications_impl(db_session, a["id"]) == []  # A sees nothing of B
    context_b = _get_patient_context_impl(db_session, b["id"])
    assert len(context_b["medications"]) == 1


# --- stdio integration: real server process + real PostgreSQL ---


def test_stdio_server_roundtrip(db_engine):
    """Spawn the real MCP server over stdio against the real test database."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from app.models import Patient as PatientModel

    settings = get_settings()
    test_db = f"{settings.POSTGRES_DB}_test"

    # committed seed on the test database (visible to the subprocess)
    seed_session = Session(bind=db_engine.connect())
    try:
        patient = PatientModel(first_name="راستی", last_name="آزمون stdio")
        seed_session.add(patient)
        seed_session.commit()

        async def run() -> None:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "app.mcp_server"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                env={**os.environ, "POSTGRES_DB": test_db},
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert sorted(t.name for t in tools.tools) == sorted(TOOL_NAMES)

                    result = await session.call_tool(
                        "get_patient", {"patient_id": patient.id}
                    )
                    assert not result.is_error
                    data = getattr(result, "structuredContent", None) or result.content
                    assert "راستی" in str(data)

                    missing = await session.call_tool(
                        "get_patient", {"patient_id": 987654321}
                    )
                    assert missing.is_error  # clean tool error, no data leak

        asyncio.run(run())
    finally:
        # remove the committed seed so later tests see a clean database
        seed_session.delete(patient)
        seed_session.commit()
        seed_session.close()
