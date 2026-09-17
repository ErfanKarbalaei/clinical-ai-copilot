"""Persistent clinical conversations (API v1) — Task 15.

Database-backed conversations for the Task-10 clinical chat. The AI call
reuses the existing provider layer and the Task-9 patient context (built
live at message time — never snapshotted); ``medication_safety=true``
reuses the Task-14 safety prompt unchanged. The stateless Task-10 endpoint
(``POST /patients/{id}/chat``) remains as-is for compatibility.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.dependencies import (
    ensure_patient_access,
    get_current_user,
    patient_from_id,
)
from app.db.session import get_db
from app.models import Conversation, ConversationMessage, Patient, User
from app.models.enums import ChatRole
from app.schemas.conversation import (
    DEFAULT_CONVERSATION_TITLE,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationMessageCreate,
    ConversationMessageResponse,
    ConversationResponse,
    SendMessageResponse,
)
from app.services import ai, evidence
from app.services.ai import AIError, AIUnavailableError
from app.services.patient_context import build_patient_context

router = APIRouter(tags=["conversations"])

logger = logging.getLogger(__name__)

CONVERSATION_NOT_FOUND_DETAIL = "گفتگو یافت نشد."
AI_NOT_CONFIGURED_DETAIL = "سرویس هوش مصنوعی تنظیم نشده است (AI_API_KEY)."
AI_PROVIDER_ERROR_DETAIL = "سرویس هوش مصنوعی پاسخ نداد؛ پیام شما ثبت شد و می‌توانید دوباره تلاش کنید."

# Most recent messages sent to the model as history (the current message is
# sent separately; patient context is always rebuilt fresh from Task 9).
MAX_HISTORY_MESSAGES = 20

# Deterministic first-message title derivation (no LLM involved).
_DERIVED_TITLE_MAX_CHARS = 50


def _get_conversation_or_404(
    db: Session, user: User, conversation_id: int
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CONVERSATION_NOT_FOUND_DETAIL,
        )
    ensure_patient_access(db, user, conversation.patient_id)
    return conversation


def _derive_title(content: str) -> str:
    """Short deterministic title from the first user message."""
    trimmed = " ".join(content.split())
    if len(trimmed) <= _DERIVED_TITLE_MAX_CHARS:
        return trimmed
    return trimmed[:_DERIVED_TITLE_MAX_CHARS] + "…"


@router.post(
    "/patients/{patient_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation for a patient",
    description=(
        "Creates an empty clinical-chat conversation. `title` is optional — "
        "the default is «گفتگوی جدید»; a short deterministic title is "
        "derived from the first message when it is sent."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def create_conversation(
    payload: ConversationCreate,
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = Conversation(
        patient_id=patient.id,
        title=(payload.title or "").strip() or DEFAULT_CONVERSATION_TITLE,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get(
    "/patients/{patient_id}/conversations",
    response_model=list[ConversationResponse],
    summary="List a patient's conversations",
    description="Most recently updated first.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def list_conversations(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.patient_id == patient.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    ).all()
    return list(conversations)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get a conversation with its messages",
    description="Conversation metadata + messages, oldest first.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": CONVERSATION_NOT_FOUND_DETAIL}
    },
)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    conversation = db.scalars(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    ).one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CONVERSATION_NOT_FOUND_DETAIL,
        )
    ensure_patient_access(db, user, conversation.patient_id)
    return conversation


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message to a conversation (persisted clinical chat)",
    description=(
        "Persists the user message, builds the patient's current context "
        "(Task 9, live) plus the recent conversation history, asks the "
        "existing AI provider, and persists the assistant answer. Every "
        "context item carries a stable evidence id (`MED-42`, `LAB-31`, …) "
        "and the answer may cite them; the backend validates every cited "
        "id against this patient's actual records and persists the "
        "validated evidence with the assistant message. Document-backed "
        "evidence is opened through the existing secure download endpoint "
        "(the model never sees URLs). `medication_safety=true` switches to "
        "the Task-14 safety prompt. If the provider fails, the user "
        "message stays persisted for traceability and NO assistant message "
        "is fabricated (502)."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": CONVERSATION_NOT_FOUND_DETAIL},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "پیام نامعتبر"},
        status.HTTP_502_BAD_GATEWAY: {"description": AI_PROVIDER_ERROR_DETAIL},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": AI_NOT_CONFIGURED_DETAIL},
    },
)
def send_conversation_message(
    conversation_id: int,
    payload: ConversationMessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SendMessageResponse:
    conversation = _get_conversation_or_404(db, user, conversation_id)
    content = payload.content.strip()

    # history BEFORE the current message: most recent N, restored to
    # chronological order (the current message is sent separately)
    history_rows = db.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.id.desc())
        .limit(MAX_HISTORY_MESSAGES)
    ).all()
    history_rows.reverse()
    history = [
        {"role": row.role.value, "content": row.content} for row in history_rows
    ]

    # persist the user message first — it remains traceable if the AI fails
    user_message = ConversationMessage(
        conversation=conversation, role=ChatRole.user, content=content
    )
    db.add(user_message)
    if not history and conversation.title == DEFAULT_CONVERSATION_TITLE:
        conversation.title = _derive_title(content)  # deterministic, no LLM
    db.commit()
    db.refresh(user_message)

    try:
        provider = ai.get_provider()
    except AIUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_NOT_CONFIGURED_DETAIL,
        ) from None

    # Patient context is ALWAYS rebuilt live (Task 9) — never snapshotted;
    # conversation history and patient context stay separate concepts.
    context = build_patient_context(db, conversation.patient)
    context_dict = context.model_dump()

    # Task 16: stable evidence ids from the REAL records + the valid-index
    # used later to validate whatever the model claims.
    evidence_index = evidence.build_evidence_index(context_dict)
    evidence.annotate_context(context_dict)

    system_prompt = (
        evidence.EVIDENCE_SAFETY_SYSTEM_PROMPT
        if payload.medication_safety
        else evidence.EVIDENCE_CHAT_SYSTEM_PROMPT
    )

    try:
        raw = provider.complete(
            system=system_prompt,
            user=ai.build_user_message(context_dict, content),
            history=history,
        )
    except AIError as error:
        # Safe Persian 502 for the client; the real provider failure is
        # logged. The user message stays persisted; nothing is fabricated.
        logger.error(
            "AI provider failure (conversation=%s): %s: %s",
            conversation.id, type(error).__name__, error,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=AI_PROVIDER_ERROR_DETAIL,
        ) from None

    # Never trust the model: only ids that exist in THIS patient's context
    # survive; foreign/fabricated ids are dropped (never transformed).
    answer, model_evidence_ids = evidence.parse_evidence_answer(raw)
    validated_evidence = evidence.validate_evidence(
        model_evidence_ids, evidence_index
    )

    assistant_message = ConversationMessage(
        conversation=conversation,
        role=ChatRole.assistant,
        content=answer,
        evidence=[item.model_dump() for item in validated_evidence] or None,
    )
    db.add(assistant_message)
    # keep list ordering meaningful (newest activity first)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_message)
    return SendMessageResponse(
        user_message=ConversationMessageResponse.model_validate(user_message),
        assistant_message=ConversationMessageResponse.model_validate(
            assistant_message
        ),
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Removes the conversation and all of its messages (cascade).",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": CONVERSATION_NOT_FOUND_DETAIL}
    },
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    conversation = _get_conversation_or_404(db, user, conversation_id)
    db.delete(conversation)
    db.commit()
    return None
