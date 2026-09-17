"""AI-assisted medication-safety analysis (decision support).

Reuses the existing provider-agnostic AI layer (Tasks 10/10.5) and the
Task-9 patient context — no second aggregation system, no new provider,
no rules. This is deliberately SEPARATE from Task 11's deterministic
rule engine (``services/medication_safety.py``): that engine is not
called, expanded, or duplicated here; the LLM analysis is the mechanism.

The model may only reason over the provided patient context plus
established pharmacological knowledge, must distinguish potential from
well-established interactions, must surface missing information and
uncertainty, and must never fabricate data or citations. Malformed model
output never reaches the client verbatim — it becomes a clean AIError.
"""

import json
import logging

from app.schemas.ai_medication_safety import MedicationCandidate
from app.schemas.patient_context import PatientContextResponse
from app.services import ai

logger = logging.getLogger(__name__)

# Safety rules shared by both surfaces (structured endpoint + chat mode).
_SAFETY_RULES_CORE = """Rules:
- Ground every statement in the provided patient context PLUS established
  pharmacological knowledge. NEVER invent medications, diagnoses, lab
  results, allergies, or patient facts that are not present in the context.
- NEVER claim an interaction exists unless it is supported by established
  knowledge or the context; clearly distinguish «تداخل احتمالی» (potential)
  from «تداخل شناخته‌شده» (well-established).
- If the available information is insufficient for a conclusion, say so
  plainly and list exactly what is missing — do not guess and do not claim
  certainty you do not have.
- Communicate uncertainty explicitly.
- No fabricated citations, references, or guideline names.
- Be concise. Respond in Persian (drug names may stay in Latin form).
- This is clinical decision support ONLY — no autonomous prescribing, no
  dose calculation; the physician makes the final decision.
"""

# Structured endpoint: strict JSON contract, parsed and validated — the
# raw model text is never exposed if it breaks this contract.
MEDICATION_SAFETY_JSON_PROMPT = (
    """You are a medication-safety decision-support assistant used by a
physician. You receive one patient's structured context (current
medications, allergies, conditions, labs, notes/documents when available)
and candidate medication(s) the physician is considering prescribing.
Analyze the medication-safety situation: drug–drug interactions with the
patient's current medications, allergy conflicts, and condition-specific
concerns.

"""
    + _SAFETY_RULES_CORE
    + """
Output format — ONLY a JSON object, no markdown, no extra text, with
exactly these keys:
- "overall_assessment": string — a short Persian overall assessment
- "interactions": array of Persian strings; prefix each item with
  «تداخل احتمالی:» or «تداخل شناخته‌شده:»
- "patient_factors": array of Persian strings — patient-specific concerns
  (conditions, allergies, labs) relevant to this prescription
- "missing_information": array of Persian strings — what is missing from
  the context for a complete assessment (empty array if nothing crucial)
- "uncertainty": string or null — an explicit statement of uncertainty
"""
)

# Chat mode: same rules, free-text labeled sections rendered in the chat
# bubble (extends the existing Task-10 chat — no second chat system).
MEDICATION_SAFETY_CHAT_PROMPT = (
    """You are a medication-safety decision-support assistant used by a
physician. You receive one patient's structured context and the
physician's medication-safety question (typically about prescribing
candidate medication(s)). Analyze interactions with current medications,
allergy conflicts, and condition-specific concerns.

"""
    + _SAFETY_RULES_CORE
    + """
Answer in Persian using ONLY these short labeled sections (omit a section
when you have nothing for it):
«ارزیابی کلی:»، «تداخل‌ها:» (each prefixed احتمالی/شناخته‌شده)،
«نکات خاص این بیمار:»، «اطلاعات ناقص:»، «عدم‌قطعیت:».
Keep the whole answer under ~250 words.
"""
)


def build_safety_question(
    medications: list[MedicationCandidate], question: str | None
) -> str:
    """Compose the physician's request: candidate medication(s) + question."""
    lines = ["Candidate medication(s) to prescribe:"]
    for medication in medications:
        dose = f" ({medication.dose})" if medication.dose else ""
        lines.append(f"- {medication.name}{dose}")
    if question and question.strip():
        lines.append(f"Physician's question: {question.strip()}")
    else:
        lines.append(
            "Physician's request: assess the safety of adding the candidate "
            "medication(s) given this patient's current medications and "
            "clinical situation."
        )
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict:
    """Locate and parse the JSON object inside a model response.

    Tolerates markdown code fences and surrounding prose; anything that is
    not a valid JSON object becomes a clean AIError (never raw exposure).
    """
    cleaned = text.strip()
    fence = cleaned.find("```")
    if fence != -1:  # drop an opening ```json fence line if present
        first_newline = cleaned.find("\n", fence)
        cleaned = (
            cleaned[:fence] + cleaned[first_newline + 1 :]
            if first_newline != -1
            else cleaned[:fence]
        )
    cleaned = cleaned.replace("```", "")

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ai.AIError("analysis response contained no JSON object")
    try:
        data = json.loads(cleaned[start : end + 1])
    except ValueError as error:
        raise ai.AIError(f"malformed analysis response: {error}") from None
    if not isinstance(data, dict):
        raise ai.AIError("analysis response is not a JSON object")
    return data


def _string_list(data: dict, key: str) -> list[str]:
    """Validate one contract list — non-string junk is dropped, wrong type fails."""
    value = data.get(key, [])
    if not isinstance(value, list):
        raise ai.AIError(f"analysis field {key!r} is not a list")
    return [
        item.strip() for item in value if isinstance(item, str) and item.strip()
    ]


def parse_analysis(raw: str) -> dict:
    """Validate/normalize the model output into the response-contract fields."""
    data = _extract_json_object(raw)

    overall = data.get("overall_assessment")
    if not isinstance(overall, str) or not overall.strip():
        raise ai.AIError("analysis response missing 'overall_assessment'")

    uncertainty = data.get("uncertainty")
    if uncertainty is not None and not isinstance(uncertainty, str):
        raise ai.AIError("analysis field 'uncertainty' is not a string")
    uncertainty = uncertainty.strip() or None if uncertainty else None

    return {
        "overall_assessment": overall.strip(),
        "interactions": _string_list(data, "interactions"),
        "patient_factors": _string_list(data, "patient_factors"),
        "missing_information": _string_list(data, "missing_information"),
        "uncertainty": uncertainty,
    }


def analyze_medication_safety(
    *,
    context: PatientContextResponse,
    medications: list[MedicationCandidate],
    question: str | None,
) -> dict:
    """One provider call → validated contract fields (raises AIError/AIUnavailableError)."""
    provider = ai.get_provider()
    raw = provider.complete(
        system=MEDICATION_SAFETY_JSON_PROMPT,
        user=ai.build_user_message(
            context.model_dump(), build_safety_question(medications, question)
        ),
    )
    analysis = parse_analysis(raw)
    logger.info(
        "AI medication-safety analysis ok (interactions=%d, patient_factors=%d, "
        "missing=%d)",
        len(analysis["interactions"]),
        len(analysis["patient_factors"]),
        len(analysis["missing_information"]),
    )
    return analysis
