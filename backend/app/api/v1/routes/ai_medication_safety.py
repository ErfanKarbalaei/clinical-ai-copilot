"""AI-assisted medication-safety endpoint (API v1).

LLM decision-support analysis of candidate medication(s) against the
patient's full Task-9 context, via the existing Gemini/AI provider.
Deliberately separate from Task 11's deterministic rule engine
(``/medications/check``) — no rules are consulted, expanded, or duplicated
here; the AI analysis is the mechanism. Nothing is persisted (on-demand,
synchronous) and the analysis never blocks any medication workflow.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import patient_from_id
from app.db.session import get_db
from app.models import Patient
from app.schemas.ai_medication_safety import (
    AiMedicationSafetyCheckRequest,
    AiMedicationSafetyCheckResponse,
)
from app.services import ai
from app.services.ai_medication_safety import analyze_medication_safety
from app.services.patient_context import build_patient_context

router = APIRouter(tags=["ai-medication-safety"])

logger = logging.getLogger(__name__)

AI_ANALYSIS_DISCLAIMER = (
    "این تحلیل توسط هوش مصنوعی ارائه شده و جایگزین قضاوت و تصمیم پزشک نیست."
)
AI_NOT_CONFIGURED_DETAIL = "سرویس هوش مصنوعی تنظیم نشده است (AI_API_KEY)."
AI_PROVIDER_ERROR_DETAIL = (
    "تحلیل ایمنی دارو انجام نشد؛ کمی بعد دوباره تلاش کنید. "
    "جریان ثبت دارو دست‌نخورده است."
)


@router.post(
    "/patients/{patient_id}/medications/ai-safety-check",
    response_model=AiMedicationSafetyCheckResponse,
    summary="AI-assisted medication-safety analysis (decision support)",
    description=(
        "Sends the candidate medication(s) (name + optional dose, 1–5 items) "
        "together with the patient's complete Task-9 context (current "
        "medications, allergies, conditions, labs, notes/documents) to the "
        "configured AI provider (Gemini). The model must ground every "
        "statement in the provided context, distinguish potential from "
        "well-established interactions, and explicitly surface missing "
        "information and uncertainty. Nothing is persisted and the analysis "
        "never blocks saving a medication. Deterministic rule-based checks "
        "remain available at `/medications/check` (Task 11)."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "درخواست نامعتبر"},
        status.HTTP_502_BAD_GATEWAY: {"description": AI_PROVIDER_ERROR_DETAIL},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": AI_NOT_CONFIGURED_DETAIL},
    },
)
def ai_medication_safety_check(
    patient_id: int,
    payload: AiMedicationSafetyCheckRequest,
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> AiMedicationSafetyCheckResponse:
    context = build_patient_context(db, patient)
    try:
        analysis = analyze_medication_safety(
            context=context,
            medications=payload.medications,
            question=payload.question,
        )
    except ai.AIUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_NOT_CONFIGURED_DETAIL,
        ) from None
    except ai.AIError as error:
        # Safe Persian 502 for the client; the real provider failure is logged.
        logger.error(
            "AI medication-safety failure (patient=%s, candidates=%s): %s: %s",
            patient.id,
            [medication.name for medication in payload.medications],
            type(error).__name__,
            error,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=AI_PROVIDER_ERROR_DETAIL,
        ) from None

    return AiMedicationSafetyCheckResponse(
        patient_id=patient.id,
        medications=payload.medications,
        disclaimer=AI_ANALYSIS_DISCLAIMER,
        generated_at=datetime.now(timezone.utc),
        **analysis,
    )
