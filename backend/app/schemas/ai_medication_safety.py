"""Pydantic schemas for the AI-assisted medication-safety analysis API.

Deliberately separate from ``schemas/medication_safety.py`` (Task 11's
deterministic rule engine): this is the LLM-assisted decision-support
analysis over the patient's Task-9 context. No rules, no rule ids.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MedicationCandidate(BaseModel):
    """One candidate medication the physician is considering prescribing."""

    name: str = Field(min_length=1, max_length=200, description="نام داروی کاندید")
    dose: str | None = Field(
        default=None, max_length=100, description="دوز پیشنهادی (اختیاری)"
    )


class AiMedicationSafetyCheckRequest(BaseModel):
    """Request for the AI-assisted safety analysis.

    Supports one or more candidate medications (relevant combinations are
    analyzed together — this is NOT a regimen-wide interaction engine).
    """

    medications: list[MedicationCandidate] = Field(
        min_length=1, max_length=5, description="دارو(های) کاندید — حداکثر ۵ مورد"
    )
    question: str | None = Field(
        default=None, max_length=2000, description="پرسش بالینی اختیاری پزشک"
    )


class AiMedicationSafetyCheckResponse(BaseModel):
    """Structured result of the AI-assisted medication-safety analysis.

    Small contract on purpose: a Persian overall assessment plus string
    lists — no invented medical structure (no severity enums, no rule ids,
    no drug codes). All content comes from the model and remains
    decision support only.
    """

    patient_id: int
    medications: list[MedicationCandidate] = Field(description="بازگشت کاندیدها")
    overall_assessment: str = Field(description="ارزیابی کلی (فارسی)")
    interactions: list[str] = Field(
        default_factory=list,
        description="نکات تداخل — هر مورد با پیشوند «تداخل احتمالی/شناخته‌شده»",
    )
    patient_factors: list[str] = Field(
        default_factory=list, description="نکات خاص این بیمار"
    )
    missing_information: list[str] = Field(
        default_factory=list, description="اطلاعات غایبِ موردنیاز برای ارزیابی کامل"
    )
    uncertainty: str | None = Field(
        default=None, description="بیان صریح عدم‌قطعیت (در صورت وجود)"
    )
    disclaimer: str = Field(description="سلب مسئولیت ثابت")
    generated_at: datetime
