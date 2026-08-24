"""Medication catalog helpers."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Medication


def get_or_create_medication(
    db: Session, name: str, generic_name: str | None = None
) -> Medication:
    """Find a catalog medication by name (case-insensitive) or create it.

    The caller owns the transaction: creation is flushed (not committed) so
    it commits or rolls back together with the patient medication record.
    """
    cleaned_name = name.strip()
    medication = db.scalars(
        select(Medication).where(func.lower(Medication.name) == cleaned_name.lower())
    ).first()
    if medication is None:
        medication = Medication(name=cleaned_name, generic_name=generic_name)
        db.add(medication)
        db.flush()
    return medication
