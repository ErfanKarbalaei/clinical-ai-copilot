"""Pydantic schemas for the medication-safety (prescription check) API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MedicationSafetyCheckRequest(BaseModel):
    """Candidate medication to check against the patient's active regimen.

    Reference the catalog by ``medication_id`` or send a free-text
    ``medication_name`` (checked by alias matching) — exactly one of the two.
    """

    medication_id: int | None = Field(
        default=None, description="شناسهٔ دارو در کاتالوگ"
    )
    medication_name: str | None = Field(
        default=None, min_length=1, max_length=200, description="نام داروی کاندید"
    )
    dosage: str | None = Field(default=None, max_length=100, description="دوز پیشنهادی")
    explain: bool = Field(
        default=False,
        description="توضیح فارسی هشدارها با مدل زبانی (اختیاری؛ هشدارها همیشه قطعی‌اند)",
    )

    @model_validator(mode="after")
    def exactly_one_medication_reference(self) -> "MedicationSafetyCheckRequest":
        has_id = self.medication_id is not None
        has_name = self.medication_name is not None
        if has_id and has_name:
            raise ValueError(
                "نمی‌توان هم medication_id و هم medication_name را ارسال کرد."
            )
        if not has_id and not has_name:
            raise ValueError("medication_id یا medication_name باید ارسال شود.")
        return self


class SafetyWarning(BaseModel):
    """One deterministic warning produced by the rule engine.

    ``rule_id`` traces the warning back to the versioned rules knowledge
    base — warnings are NEVER invented by an LLM.
    """

    warning_type: Literal["drug_interaction", "allergy_conflict", "duplicate_therapy"]
    severity: Literal["mild", "moderate", "severe"]
    title: str
    detail: str
    rule_id: str
    involved: list[str] = Field(description="نام داروهای/مواد مرتبط با هشدار")


class MedicationSafetyCheckResponse(BaseModel):
    """Result of a deterministic prescription-safety check."""

    patient_id: int
    candidate_name: str
    candidate_class_labels: list[str] = Field(
        description="کلاس‌های دارویی شناسایی‌شده برای کاندید"
    )
    candidate_covered: bool = Field(
        description="آیا کاندید در پایگاه قواعد شناخته شده است"
    )
    warnings: list[SafetyWarning]
    rules_version: str
    checked_at: datetime
    explanation: str | None = Field(
        default=None, description="توضیح اختیاری هشدارها توسط مدل زبانی"
    )
    explanation_disclaimer: str | None = None
