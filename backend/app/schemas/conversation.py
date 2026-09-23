"""Pydantic schemas for the persistent clinical-conversation API (Task 15)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ChatRole

DEFAULT_CONVERSATION_TITLE = "گفتگوی جدید"


class ConversationCreate(BaseModel):
    """Payload for creating a conversation (title optional)."""

    title: str | None = Field(
        default=None, min_length=1, max_length=300, description="عنوان گفتگو"
    )


class EvidenceItemResponse(BaseModel):
    """One validated piece of patient-record evidence (Task 16).

    ``document_id`` points to the ORIGINAL source document when a real
    relationship exists — the frontend opens it via the existing secure
    document download endpoint. No URLs are stored or returned here.
    """

    source_id: str = Field(description="شناسهٔ پایدار شواهد، مثال LAB-31")
    source_type: str = Field(description="نوع رکورد منبع")
    description: str = Field(description="توصیف خوانا از رکورد واقعی")
    document_id: int | None = Field(
        default=None, description="سند منبع اصلی (در صورت وجود)"
    )


class ConversationMessageResponse(BaseModel):
    """One persisted message (user question or assistant answer)."""

    id: int
    conversation_id: int
    role: ChatRole
    content: str
    evidence: list[EvidenceItemResponse] = Field(
        default_factory=list,
        description="شواهد اعتبارسنجی‌شدهٔ پاسخ (فقط برای پیام‌های دستیار)",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("evidence", mode="before")
    @classmethod
    def _none_becomes_empty(cls, value):
        """Pre-Task-16 rows (and user messages) store NULL → render as []."""
        return value or []


class ConversationResponse(BaseModel):
    """Conversation metadata (message list included in the detail view)."""

    id: int
    patient_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    """Conversation metadata + its messages, oldest first."""

    messages: list[ConversationMessageResponse]


class ConversationMessageCreate(BaseModel):
    """Payload for sending a message into a conversation."""

    content: str = Field(min_length=1, max_length=2000, description="پیام پزشک")
    medication_safety: bool = Field(
        default=False,
        description=(
            "حالت تحلیل ایمنی دارو (تسک ۱۴): با true بودن، پاسخ با پرامپت "
            "تخصصی ایمنی دارو تولید می‌شود"
        ),
    )
    # Runtime provider/model selection (ids only — URLs/keys are never
    # accepted from the client). Omitted → environment defaults.
    provider: str | None = Field(
        default=None, max_length=40, description="شناسهٔ ارائه‌دهندهٔ هوش مصنوعی"
    )
    model: str | None = Field(
        default=None, max_length=200, description="شناسهٔ مدل هوش مصنوعی"
    )


class SendMessageResponse(BaseModel):
    """Result of one exchange: the persisted user message + AI answer."""

    user_message: ConversationMessageResponse
    assistant_message: ConversationMessageResponse
