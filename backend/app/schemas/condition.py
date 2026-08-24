"""Pydantic schemas for the condition API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConditionStatus


class ConditionBase(BaseModel):
    """Shared condition fields."""

    name: str = Field(min_length=1, max_length=200, description="نام بیماری/مشکل بالینی")
    status: ConditionStatus = Field(
        default=ConditionStatus.active, description="وضعیت (active/resolved)"
    )
    onset_date: date | None = Field(default=None, description="تاریخ شروع")
    resolved_date: date | None = Field(default=None, description="تاریخ رفع")
    notes: str | None = Field(default=None, description="یادداشت")


class ConditionCreate(ConditionBase):
    """Payload for creating a patient condition."""


class ConditionUpdate(BaseModel):
    """Payload for partially updating a condition (PATCH — all optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: ConditionStatus | None = None
    onset_date: date | None = None
    resolved_date: date | None = None
    notes: str | None = None


class ConditionResponse(ConditionBase):
    """Condition representation returned by the API."""

    id: int
    patient_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
