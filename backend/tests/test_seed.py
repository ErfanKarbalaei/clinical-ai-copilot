"""Tests for the development seed script (require a running PostgreSQL)."""

import pytest
from sqlalchemy import select

from app.models import Patient
from app.models.enums import AllergySeverity, NoteSource
from scripts import seed


def test_seed_creates_expected_row_counts(db_session):
    counts = seed.run(session=db_session, reset=True)

    assert counts == {
        "patients": 3,
        "conditions": 5,
        "medications": 4,
        "patient_medications": 4,
        "allergies": 2,
        "documents": 3,
        "voice_notes": 3,
        "clinical_notes": 3,
        "lab_results": 5,
        "clinical_events": 19,
    }


def test_seed_data_is_queryable_and_linked(db_session):
    seed.run(session=db_session, reset=True)

    ali = db_session.scalars(
        select(Patient).where(
            Patient.first_name == "علی", Patient.last_name == "رضایی"
        )
    ).one()
    assert len(ali.conditions) == 2
    assert len(ali.patient_medications) == 2
    assert ali.allergies[0].severity is AllergySeverity.severe
    assert len(ali.lab_results) == 3
    assert len(ali.clinical_events) == 8  # timeline events exist

    # The clinical note derived from the voice recording links back to it.
    maryam = db_session.scalars(
        select(Patient).where(Patient.first_name == "مریم")
    ).one()
    voice_note = maryam.voice_notes[0]
    derived = [
        note
        for note in maryam.clinical_notes
        if note.voice_note_id == voice_note.id
    ]
    assert derived, "expected a clinical note linked to the voice note"
    assert derived[0].source is NoteSource.voice


def test_seed_without_reset_refuses_when_data_exists(db_session):
    seed.run(session=db_session, reset=True)

    with pytest.raises(RuntimeError):
        seed.run(session=db_session, reset=False)

    # ...and reset=True safely reseeds.
    counts = seed.run(session=db_session, reset=True)
    assert counts["patients"] == 3
