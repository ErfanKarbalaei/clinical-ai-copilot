"""AI-assisted medication-safety tests (provider mocked — no real LLM calls).

Covers the structured endpoint (Use Case 2) and the chat medication-safety
mode (Use Case 1). Task 11's rule engine is NOT involved anywhere.
"""

import pytest

from app.api.v1.routes.ai_medication_safety import AI_ANALYSIS_DISCLAIMER
from app.services import ai
from app.services.ai_medication_safety import (
    MEDICATION_SAFETY_CHAT_PROMPT,
    MEDICATION_SAFETY_JSON_PROMPT,
    build_safety_question,
    parse_analysis,
)

PATIENTS_URL = "/api/v1/patients"
CHECK_URL = "/api/v1/patients/{patient_id}/medications/ai-safety-check"
CHAT_URL = "/api/v1/patients/{patient_id}/chat"

VALID_JSON = """{
  "overall_assessment": "تجویز با احتیاط قابل بررسی است.",
  "interactions": ["تداخل احتمالی: با وارفارین، خطر خونریزی"],
  "patient_factors": ["سن بالا"],
  "missing_information": ["عملکرد کلیه ثبت نشده است"],
  "uncertainty": "اطلاعات آزمایشگاهی ناقص است"
}"""


class FakeProvider:
    """Records prompts; returns a canned response or raises."""

    def __init__(self, response: str = VALID_JSON, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def complete(self, *, system: str, user: str, history=None) -> str:
        self.calls.append({"system": system, "user": user, "history": history})
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture()
def fake_provider(monkeypatch):
    holder: dict = {}

    def install(response: str = VALID_JSON, error: Exception | None = None):
        provider = FakeProvider(response=response, error=error)
        holder["provider"] = provider
        monkeypatch.setattr(ai, "get_provider", lambda: provider)
        return provider

    return install


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL,
            json={"first_name": "آزمون", "last_name": f"ایمنی {suffix}"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def _check(api_client, patient_id: int, payload: dict):
    return api_client.post(CHECK_URL.format(patient_id=patient_id), json=payload)


# --- prompt building + parsing (unit) ---


def test_safety_prompts_are_safety_scoped():
    for prompt in (MEDICATION_SAFETY_JSON_PROMPT, MEDICATION_SAFETY_CHAT_PROMPT):
        assert "NEVER invent medications" in prompt
        assert "تداخل احتمالی" in prompt  # potential vs established distinction
        assert "uncertainty" in prompt.lower()
        assert "No fabricated citations" in prompt
        assert "decision support ONLY" in prompt


def test_build_safety_question_candidates_and_question():
    from app.schemas.ai_medication_safety import MedicationCandidate

    message = build_safety_question(
        [
            MedicationCandidate(name="Warfarin", dose="5 mg"),
            MedicationCandidate(name="Aspirin"),
        ],
        "با داروهای فعلی تداخل دارد؟",
    )
    assert "Warfarin (5 mg)" in message
    assert "Aspirin" in message
    assert "تداخل دارد؟" in message


def test_parse_analysis_strips_fences_and_validates():
    fenced = "```json\n" + VALID_JSON + "\n```"
    parsed = parse_analysis(fenced)
    assert parsed["overall_assessment"].startswith("تجویز")
    assert parsed["interactions"] == ["تداخل احتمالی: با وارفارین، خطر خونریزی"]
    assert parsed["missing_information"] == ["عملکرد کلیه ثبت نشده است"]
    assert parsed["uncertainty"] == "اطلاعات آزمایشگاهی ناقص است"


def test_parse_analysis_defaults_empty_lists():
    parsed = parse_analysis('{"overall_assessment": "خطر خاصی دیده نشد."}')
    assert parsed["interactions"] == []
    assert parsed["patient_factors"] == []
    assert parsed["missing_information"] == []
    assert parsed["uncertainty"] is None


# --- structured endpoint (Use Case 2) ---


def test_check_returns_structured_analysis(api_client, make_patient, fake_provider):
    provider = fake_provider()
    patient = make_patient("۱")

    response = _check(
        api_client,
        patient["id"],
        {
            "medications": [{"name": "وارفارین", "dose": "5 mg"}],
            "question": "با داروهای فعلی تداخل دارد؟",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patient_id"] == patient["id"]
    assert body["medications"] == [{"name": "وارفارین", "dose": "5 mg"}]
    assert body["overall_assessment"].startswith("تجویز")
    assert body["interactions"]
    assert body["disclaimer"] == AI_ANALYSIS_DISCLAIMER
    assert body["generated_at"]
    # the provider got the JSON contract + the candidate + the question
    assert MEDICATION_SAFETY_JSON_PROMPT == provider.calls[0]["system"]
    assert "وارفارین (5 mg)" in provider.calls[0]["user"]
    assert "تداخل دارد؟" in provider.calls[0]["user"]


def test_check_includes_patient_context(api_client, db_session, make_patient, fake_provider):
    provider = fake_provider()
    patient = make_patient("۲")
    api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/conditions",
        json={"name": "دیابت نوع ۲"},
    )
    api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/medications",
        json={"medication_name": "Metformin 500", "dosage": "500 mg"},
    )

    response = _check(
        api_client, patient["id"], {"medications": [{"name": "Warfarin"}]}
    )

    assert response.status_code == 200
    user_message = provider.calls[0]["user"]
    # Task-9 context is reused (not a second aggregation): meds + conditions present
    assert "Metformin 500" in user_message
    assert "دیابت نوع ۲" in user_message
    assert user_message.startswith("Patient record (JSON):")


def test_check_empty_context_still_analyzes(api_client, make_patient, fake_provider):
    """Incomplete patient context must not block the analysis (missing info surfaces)."""
    fake_provider()
    patient = make_patient("۳")  # no meds / conditions / allergies at all

    response = _check(api_client, patient["id"], {"medications": [{"name": "Aspirin"}]})

    assert response.status_code == 200
    assert response.json()["missing_information"]  # model-reported missing info passes through


def test_check_multiple_medications(api_client, make_patient, fake_provider):
    provider = fake_provider()
    patient = make_patient("۴")

    response = _check(
        api_client,
        patient["id"],
        {"medications": [{"name": "Warfarin"}, {"name": "Aspirin", "dose": "81 mg"}]},
    )

    assert response.status_code == 200
    user_message = provider.calls[0]["user"]
    assert "Warfarin" in user_message and "Aspirin (81 mg)" in user_message


def test_check_malformed_json_maps_to_502(api_client, make_patient, fake_provider):
    fake_provider(response="متأسفانه نمی‌توانم تحلیل کنم.")  # prose, no JSON

    response = _check(
        api_client, make_patient("۵")["id"], {"medications": [{"name": "Warfarin"}]}
    )
    # never a fake analysis, never raw model prose
    assert response.status_code == 502
    assert "analysis" not in response.json()


def test_check_missing_overall_assessment_maps_to_502(api_client, make_patient, fake_provider):
    fake_provider(response='{"interactions": ["تداخل احتمالی: x"]}')

    response = _check(api_client, make_patient("۶")["id"], {"medications": [{"name": "X"}]})

    assert response.status_code == 502


def test_check_wrong_field_type_maps_to_502(api_client, make_patient, fake_provider):
    fake_provider(
        response='{"overall_assessment": "ok", "interactions": "یک متن نه فهرست"}'
    )

    response = _check(api_client, make_patient("۷")["id"], {"medications": [{"name": "X"}]})

    assert response.status_code == 502


def test_check_provider_failure_maps_to_502(api_client, make_patient, fake_provider):
    fake_provider(error=ai.AIError("provider down"))

    response = _check(api_client, make_patient("۸")["id"], {"medications": [{"name": "X"}]})

    assert response.status_code == 502


def test_check_unconfigured_maps_to_503(api_client, make_patient, monkeypatch):
    def unavailable():
        raise ai.AIUnavailableError("AI_API_KEY is not configured")

    monkeypatch.setattr(ai, "get_provider", unavailable)

    response = _check(api_client, make_patient("۹")["id"], {"medications": [{"name": "X"}]})

    assert response.status_code == 503


def test_check_unknown_patient_404(api_client, fake_provider):
    fake_provider()
    response = _check(api_client, 999999, {"medications": [{"name": "X"}]})
    assert response.status_code == 404


def test_check_validation_422(api_client, make_patient, fake_provider):
    fake_provider()
    patient = make_patient("۱۰")

    empty = _check(api_client, patient["id"], {"medications": []})
    assert empty.status_code == 422

    too_many = _check(
        api_client,
        patient["id"],
        {"medications": [{"name": f"drug-{i}"} for i in range(6)]},
    )
    assert too_many.status_code == 422

    anonymous = _check(api_client, patient["id"], {"medications": [{"dose": "5 mg"}]})
    assert anonymous.status_code == 422


# --- chat integration (Use Case 1) ---


def test_chat_medication_safety_flag_switches_prompt(api_client, make_patient, fake_provider):
    provider = fake_provider()
    patient = make_patient("۱۱")

    flagged = api_client.post(
        CHAT_URL.format(patient_id=patient["id"]),
        json={
            "question": "می‌خواهم وارفارین تجویز کنم؛ تداخل دارد؟",
            "medication_safety": True,
        },
    )
    assert flagged.status_code == 200
    assert provider.calls[0]["system"] == MEDICATION_SAFETY_CHAT_PROMPT
    assert "وارفارین" in provider.calls[0]["user"]

    plain = api_client.post(
        CHAT_URL.format(patient_id=patient["id"]),
        json={"question": "خلاصهٔ وضعیت بیمار؟"},
    )
    assert plain.status_code == 200
    assert provider.calls[1]["system"] == ai.SYSTEM_PROMPT  # default unchanged


def test_chat_safety_mode_keeps_history_and_context(api_client, db_session, make_patient, fake_provider):
    provider = fake_provider()
    patient = make_patient("۱۲")
    api_client.post(
        f"{PATIENTS_URL}/{patient['id']}/allergies",
        json={"allergen": "Penicillin", "severity": "severe"},
    )

    response = api_client.post(
        CHAT_URL.format(patient_id=patient["id"]),
        json={
            "question": "برای این بیمار آموکسی‌سیلین تجویز کنم؟",
            "history": [{"role": "user", "content": "سابقه آلرژی دارد؟"}],
            "medication_safety": True,
        },
    )

    assert response.status_code == 200
    call = provider.calls[0]
    assert "Penicillin" in call["user"]  # Task-9 context (incl. allergies) reused
    assert call["history"] == [{"role": "user", "content": "سابقه آلرژی دارد؟"}]
