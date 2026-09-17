"""Pydantic schemas for the persistent clinical-conversation API (Task 15)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ChatRole

DEFAULT_CONVERSATION_TITLE = "گفتگوی جدید"


class ConversationCreate(BaseModel):
    """Payload for creating a conversation (title optional)."""

    title: str | None = Field(
        default=None, min_length=1, max_length=300, description="عنوان گفتگو"
    )


class ConversationMessageResponse(BaseModel):
    """One persisted message (user question or assistant answer)."""

    id: int
    conversation_id: int
    role: ChatRole
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class SendMessageResponse(BaseModel):
    """Result of one exchange: the persisted user message + AI answer."""

    user_message: ConversationMessageResponse
    assistant_message: ConversationMessageResponse
