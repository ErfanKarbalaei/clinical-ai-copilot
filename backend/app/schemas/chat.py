"""Pydantic schemas for the clinical AI assistant (chat) API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    """One previous question/answer turn (kept client-side, sent for context)."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000, description="پرسش پزشک")
    history: list[ChatHistoryItem] = Field(
        default_factory=list, max_length=20, description="نوبت‌های قبلی گفتگو"
    )


class ChatResponse(BaseModel):
    patient_id: int
    question: str
    answer: str
    generated_at: datetime
