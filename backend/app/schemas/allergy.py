"""Pydantic schemas for the allergy API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AllergySeverity


class AllergyBase(BaseModel):
    """Shared allergy fields."""

    allergen: str = Field(min_length=1, max_length=200, description="عامل حساسیت")
    reaction: str | None = Field(default=None, max_length=300, description="واکنش")
    severity: AllergySeverity = Field(
        default=AllergySeverity.unknown,
        description="شدت (mild/moderate/severe/unknown)",
    )


class AllergyCreate(AllergyBase):
    """Payload for creating a patient allergy."""


class AllergyUpdate(BaseModel):
    """Payload for partially updating an allergy (PATCH — all optional)."""

    allergen: str | None = Field(default=None, min_length=1, max_length=200)
    reaction: str | None = Field(default=None, max_length=300)
    severity: AllergySeverity | None = None


class AllergyResponse(AllergyBase):
    """Allergy representation returned by the API."""

    id: int
    patient_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
