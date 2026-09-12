"""Medication-safety tests: rule engine units (pure) + API lifecycle.

The rule engine is deterministic and DB-free, so its tests run everywhere;
API tests need PostgreSQL (auto-skipped otherwise, like the other suites).
"""

import pytest

from app.services import ai
from app.services.medication_safety import (
    check_medication_safety,
    class_labels,
    load_rules_kb,
    match_classes,
    normalize_drug_name,
)

PATIENTS_URL = "/api/v1/patients"
CHECK_URL = "/api/v1/patients/{patient_id}/medications/check"


# --- knowledge base integrity ---


def test_rules_kb_loads_and_is_consistent():
    kb = load_rules_kb()
    assert kb.version
    assert len(kb.classes) >= 25
    assert len(kb.interactions) >= 25
    valid_severities = {"mild", "moderate", "severe"}
    for rule in kb.interactions:
        assert rule.severity in valid_severities
        assert len(rule.classes) >= 2
        assert rule.classes <= set(kb.classes)  # every class referenced exists
    for cross in kb.cross_reactivity:
        assert cross.allergen_class in kb.classes
        assert cross.candidate_class in kb.classes


# --- normalization / alias matching ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Metformin 500 mg", "metformin"),
        ("  Amlodipine-5 ", "amlodipine"),
        ("پنی‌سیلین (Penicillin)", "پنی سیلین penicillin"),  # ZWNJ → space, parens stripped
        ("آسپرین ۸۰", "آسپرین"),
    ],
)
def test_normalize_drug_name(raw, expected):
    assert normalize_drug_name(raw) == expected


@pytest.mark.parametrize(
    ("name", "expected_class"),
    [
        ("Metformin 500", "metformin"),
        ("گلوکوفاژ", "metformin"),          # Persian brand
        ("بروفن", "nsaid"),                  # Persian brand for ibuprofen
        ("Augmentin 625", "penicillin"),     # co-amoxiclav brand
        ("Losartan 50", "arb"),
        ("warfarin sodium", "warfarin"),
        ("Vitamin C", None),                 # unknown → no class
    ],
)
def test_match_classes(name, expected_class):
    classes = match_classes(name)
    if expected_class is None:
        assert not classes
    else:
        assert expected_class in classes


# --- deterministic checks (pure engine) ---


def _check(candidate, active=(), allergies=()):
    return check_medication_safety(
        candidate_name=candidate,
        active_medication_names=list(active),
        allergen_names=list(allergies),
    )


def _rule_ids(result):
    return {warning.rule_id for warning in result.warnings}


def test_nsaid_with_warfarin_is_severe_interaction():
    result = _check("Ibuprofen 400", active=["Warfarin 5mg"])
    warning = next(w for w in result.warnings if w.rule_id == "INT-001")
    assert warning.severity == "severe"
    assert warning.warning_type == "drug_interaction"
    assert "Ibuprofen 400" in warning.involved and "Warfarin 5mg" in warning.involved


def test_triple_whammy_detected():
    result = _check("Diclofenac", active=["Furosemide 40", "Enalapril 10"])
    assert "INT-006" in _rule_ids(result)  # nsaid + loop + acei


def test_warfarin_plus_doac_flagged_severe():
    result = _check("Rivaroxaban 20", active=["Warfarin"])
    assert "INT-003" in _rule_ids(result)


def test_same_class_allergy_is_severe():
    result = _check("Amoxicillin", allergies=["پنی‌سیلین (Penicillin)"])
    warning = result.warnings[0]
    assert warning.warning_type == "allergy_conflict"
    assert warning.severity == "severe"
    assert warning.rule_id == "XALL-000"


def test_cross_reactivity_penicillin_to_cephalosporin():
    result = _check("Cephalexin", allergies=["پنی‌سیلین (Penicillin)"])
    warning = next(w for w in result.warnings if w.rule_id == "XALL-001")
    assert warning.severity == "moderate"
    assert warning.warning_type == "allergy_conflict"


def test_duplicate_therapy_same_class():
    result = _check("Naproxen", active=["Ibuprofen 400"])
    duplicates = [w for w in result.warnings if w.warning_type == "duplicate_therapy"]
    assert duplicates and duplicates[0].rule_id == "DUP-000"


def test_insulin_duplicates_are_allowed():
    result = _check("Insulin Glargine", active=["Insulin Aspart"])
    assert not [w for w in result.warnings if w.warning_type == "duplicate_therapy"]


def test_unknown_drugs_produce_no_warnings():
    result = _check("Vitamin C 1000", active=["Omega 3"], allergies=["گرد و غبار"])
    assert result.warnings == []
    assert result.candidate_classes == frozenset()


def test_severity_ordering_severe_first():
    result = _check("Aspirin", active=["Warfarin", "Prednisolone"])
    severities = [w.severity for w in result.warnings]
    ranks = {"severe": 0, "moderate": 1, "mild": 2}
    assert severities == sorted(severities, key=lambda s: ranks[s])


def test_class_labels_are_persian():
    labels = class_labels(match_classes("Metformin 500"))
    assert labels and any("متفورمین" in label for label in labels)


# --- API (needs PostgreSQL) ---


@pytest.fixture()
def make_patient(api_client):
    def _make(suffix: str) -> dict:
        response = api_client.post(
            PATIENTS_URL, json={"first_name": "آزمون", "last_name": f"ایمنی {suffix}"}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture()
def regimen_patient(api_client, make_patient):
    """Patient on Losartan + Metformin with a penicillin allergy."""
    patient = make_patient("۱")
    pid = patient["id"]
    api_client.post(
        f"{PATIENTS_URL}/{pid}/medications", json={"medication_name": "Losartan 50"}
    ).raise_for_status()
    api_client.post(
        f"{PATIENTS_URL}/{pid}/medications", json={"medication_name": "Metformin 500"}
    ).raise_for_status()
    api_client.post(
        f"{PATIENTS_URL}/{pid}/allergies",
        json={"allergen": "پنی‌سیلین (Penicillin)", "severity": "severe"},
    ).raise_for_status()
    return patient


def test_api_check_interaction_with_regimen(api_client, regimen_patient):
    response = api_client.post(
        CHECK_URL.format(patient_id=regimen_patient["id"]),
        json={"medication_name": "Ibuprofen 400"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_covered"] is True
    assert any("ضدالتهاب" in label for label in body["candidate_class_labels"])
    assert "INT-005" in {w["rule_id"] for w in body["warnings"]}  # nsaid + arb
    assert body["rules_version"]
    assert body["checked_at"]
    assert body["explanation"] is None  # not requested


def test_api_check_allergy_conflict(api_client, regimen_patient):
    body = api_client.post(
        CHECK_URL.format(patient_id=regimen_patient["id"]),
        json={"medication_name": "Amoxicillin 500"},
    ).json()

    allergy_warnings = [
        w for w in body["warnings"] if w["warning_type"] == "allergy_conflict"
    ]
    assert allergy_warnings[0]["severity"] == "severe"
    assert allergy_warnings[0]["rule_id"] == "XALL-000"


def test_api_check_duplicate_therapy(api_client, regimen_patient):
    body = api_client.post(
        CHECK_URL.format(patient_id=regimen_patient["id"]),
        json={"medication_name": "Metformin 850"},
    ).json()

    assert any(w["warning_type"] == "duplicate_therapy" for w in body["warnings"])


def test_api_check_unknown_candidate_has_no_warnings(api_client, regimen_patient):
    body = api_client.post(
        CHECK_URL.format(patient_id=regimen_patient["id"]),
        json={"medication_name": "Vitamin D"},
    ).json()

    assert body["warnings"] == []
    assert body["candidate_covered"] is False
    assert body["candidate_class_labels"] == []


def test_api_check_by_catalog_medication_id(api_client, regimen_patient):
    created = api_client.post(
        f"{PATIENTS_URL}/{regimen_patient['id']}/medications",
        json={"medication_name": "Azithromycin", "status": "stopped"},
    ).json()  # stopped → must NOT participate in checks

    body = api_client.post(
        CHECK_URL.format(patient_id=regimen_patient["id"]),
        json={"medication_id": created["medication"]["id"]},
    ).json()

    assert body["candidate_name"] == "Azithromycin"
    assert body["warnings"] == []  # stopped azithro vs losartan/metformin: none


def test_api_check_validation_and_404s(api_client, regimen_patient):
    url = CHECK_URL.format(patient_id=regimen_patient["id"])

    both = api_client.post(url, json={"medication_id": 1, "medication_name": "x"})
    neither = api_client.post(url, json={"dosage": "10 mg"})
    assert both.status_code == 422 and neither.status_code == 422

    missing_drug = api_client.post(url, json={"medication_id": 999999})
    assert missing_drug.status_code == 404

    missing_patient = api_client.post(
        CHECK_URL.format(patient_id=999999), json={"medication_name": "x"}
    )
    assert missing_patient.status_code == 404


def test_api_explain_uses_llm_only_for_wording(api_client, regimen_patient, monkeypatch):
    captured: dict = {}

    class FakeProvider:
        def complete(self, *, system, user, history=None):
            captured["system"] = system
            captured["user"] = user
            return "  توضیح آزمایشی هشدارها  "

    monkeypatch.setattr(ai, "get_provider", lambda: FakeProvider())

    body = api_client.post(
        CHECK_URL.format(patient_id=regimen_patient["id"]),
        json={"medication_name": "Amoxicillin", "explain": True},
    ).json()

    assert body["explanation"] == "توضیح آزمایشی هشدارها"
    assert body["explanation_disclaimer"]
    # the LLM prompt contains ONLY the deterministic warnings
    assert "XALL-000" in captured["user"]
    assert "never add new warnings" in captured["system"]
    # warnings unchanged by the explanation
    assert body["warnings"][0]["rule_id"] == "XALL-000"


def test_api_explain_survives_provider_outage(api_client, regimen_patient, monkeypatch):
    class BrokenProvider:
        def complete(self, **kwargs):
            raise ai.AIError("provider down")

    monkeypatch.setattr(ai, "get_provider", lambda: BrokenProvider())

    response = api_client.post(
        CHECK_URL.format(patient_id=regimen_patient["id"]),
        json={"medication_name": "Ibuprofen", "explain": True},
    )

    assert response.status_code == 200  # safety result never depends on the LLM
    body = response.json()
    assert body["explanation"] is None
    assert "INT-005" in {w["rule_id"] for w in body["warnings"]}


def test_api_existing_chat_still_works(api_client, regimen_patient, monkeypatch):
    """Task-10 chat must not be broken by this subsystem."""

    class FakeProvider:
        def complete(self, **kwargs):
            return "پاسخ چت"

    monkeypatch.setattr(ai, "get_provider", lambda: FakeProvider())
    response = api_client.post(
        f"{PATIENTS_URL}/{regimen_patient['id']}/chat",
        json={"question": "وضعیت بیمار؟"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "پاسخ چت"
