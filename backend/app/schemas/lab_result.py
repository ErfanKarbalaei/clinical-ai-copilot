"""Pydantic schemas for lab results (response only — used in patient overview)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ResultFlag


class LabResultResponse(BaseModel):
    """A single structured lab value."""

    id: int
    patient_id: int
    document_id: int | None = None
    test_name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None
    flag: ResultFlag | None = None
    result_date: date | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
