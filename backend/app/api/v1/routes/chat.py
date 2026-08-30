"""Clinical AI assistant endpoint (API v1) — question + patient context → answer.

Grounding: the answer is built ONLY from the patient's structured context
(Task 9) plus the physician's question. No RAG, no vector search, no web
retrieval. Decision support only — the final decision rests with the physician.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import patient_from_id
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Patient
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import ai
from app.services.ai import AIError, AIUnavailableError
from app.services.patient_context import build_patient_context

router = APIRouter(tags=["ai-assistant"])

AI_NOT_CONFIGURED_DETAIL = "سرویس هوش مصنوعی تنظیم نشده است (AI_API_KEY)."
AI_PROVIDER_ERROR_DETAIL = "سرویس هوش مصنوعی پاسخ نداد؛ کمی بعد دوباره تلاش کنید."


@router.post(
    "/patients/{patient_id}/chat",
    response_model=ChatResponse,
    summary="Ask the clinical AI assistant a question about this patient",
    description=(
        "Stateless clinical Q&A: the patient's complete structured context "
        "(demographics, conditions, medications, allergies, labs, documents, "
        "transcripts, notes) plus the physician's question are sent to a "
        "ready-to-use model. Optional `history` carries previous turns for "
        "follow-up questions. Decision support only — no RAG, no autonomous "
        "diagnosis or prescription."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"},
        status.HTTP_502_BAD_GATEWAY: {"description": AI_PROVIDER_ERROR_DETAIL},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": AI_NOT_CONFIGURED_DETAIL},
    },
)
def ask_clinical_question(
    patient_id: int,
    payload: ChatRequest,
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        provider = ai.get_provider()
    except AIUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_NOT_CONFIGURED_DETAIL,
        ) from None

    context = build_patient_context(db, patient)
    history = [item.model_dump() for item in payload.history][
        -get_settings().AI_MAX_HISTORY_TURNS:
    ]

    try:
        answer = provider.complete(
            system=ai.SYSTEM_PROMPT,
            user=ai.build_user_message(context.model_dump(), payload.question),
            history=history,
        )
    except AIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=AI_PROVIDER_ERROR_DETAIL,
        ) from None

    return ChatResponse(
        patient_id=patient.id,
        question=payload.question,
        answer=answer.strip(),
        generated_at=datetime.now(timezone.utc),
    )
