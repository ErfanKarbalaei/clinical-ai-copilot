"""Voice-note endpoints (API v1) — Persian speech-to-text workflows.

Two workflows (per the project spec):
- physician note  : doctor dictates → transcript → review → clinical note
- doctor–patient  : conversation → transcript (speaker-diarized) → review

The original audio is preserved unchanged in object storage; the transcript
is raw model output and never automatically becomes a diagnosis or note.
"""

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import (
    ensure_patient_access,
    get_current_user,
    patient_from_id,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models import ClinicalEvent, ClinicalNote, Patient, User, VoiceNote
from app.models.enums import ConversationType, TranscriptionStatus
from app.schemas.clinical_note import ClinicalNoteResponse
from app.schemas.voice_note import (
    CreateNoteFromTranscript,
    VoiceNoteResponse,
    VoiceNoteUpdate,
)
from app.services import storage
from app.services.storage import StorageError
from app.services.voice_notes import process_voice_note

router = APIRouter(tags=["voice-notes"])

VOICE_NOTE_NOT_FOUND_DETAIL = "یادداشت صوتی یافت نشد."
INVALID_AUDIO_TYPE_DETAIL = "قالب صوتی مجاز نیست. فرمت‌های مجاز: WebM، OGG/Opus، MP3، M4A/MP4، WAV و FLAC."
AUDIO_TOO_LARGE_DETAIL = "حجم فایل صوتی بیش از حد مجاز است (حداکثر ۵۰ مگابایت)."
AUDIO_NAME_TOO_LONG_DETAIL = "نام فایل بیش از حد طولانی است."
STORAGE_UNAVAILABLE_DETAIL = "سرویس ذخیره‌سازی فایل در دسترس نیست."
TRANSCRIPTION_ALREADY_RUNNING_DETAIL = "این یادداشت صوتی هم‌اکنون در حال تبدیل است."

ALLOWED_AUDIO_MIME_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/flac",
    "video/webm",  # some browsers tag MediaRecorder output this way
}
MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024
MAX_AUDIO_NAME_LENGTH = 300


def _get_voice_note_or_404(
    db: Session, user: User, voice_note_id: int
) -> VoiceNote:
    voice_note = db.get(VoiceNote, voice_note_id)
    if voice_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=VOICE_NOTE_NOT_FOUND_DETAIL,
        )
    ensure_patient_access(db, user, voice_note.patient_id)
    return voice_note


@router.post(
    "/patients/{patient_id}/voice-notes",
    response_model=VoiceNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a voice note for a patient",
    description=(
        "Multipart upload: `file` (audio) plus optional `title`, "
        "`conversation_type` (physician_note | doctor_patient) and "
        "`duration_seconds`. The original audio is preserved unchanged; "
        "Persian speech-to-text (Speechmatics) runs automatically after the "
        "upload — follow `transcription_status`. When an AI provider is "
        "configured, a best-effort cleanup then formats the raw transcript "
        "into a concise clinical note (`cleaned_note`) — formatting only, "
        "the raw transcript always stays the source of truth. Doctor–patient "
        "recordings are transcribed with speaker diarization."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "فایل نامعتبر"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": STORAGE_UNAVAILABLE_DETAIL},
    },
)
async def upload_voice_note(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="فایل صوتی"),
    title: str | None = Form(default=None, description="عنوان"),
    conversation_type: ConversationType = Form(
        default=ConversationType.physician_note, description="نوع گفتگو"
    ),
    duration_seconds: int | None = Form(
        default=None, description="مدت ضبط (ثانیه)"
    ),
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> VoiceNote:
    file_name = file.filename or "recording.webm"
    content_type = (file.content_type or "").split(";")[0].strip()

    if len(file_name) > MAX_AUDIO_NAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=AUDIO_NAME_TOO_LONG_DETAIL,
        )
    if content_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=INVALID_AUDIO_TYPE_DETAIL,
        )

    data = await file.read()
    if not data or len(data) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=AUDIO_TOO_LARGE_DETAIL if data else INVALID_AUDIO_TYPE_DETAIL,
        )

    try:
        storage_key = storage.upload_file(
            patient_id=patient.id,
            file_name=file_name,
            content_type=content_type,
            data=data,
            folder="voice",
        )
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STORAGE_UNAVAILABLE_DETAIL,
        ) from None

    voice_note = VoiceNote(
        patient_id=patient.id,
        title=(title or "").strip() or None,
        conversation_type=conversation_type,
        audio_storage_key=storage_key,
        duration_seconds=duration_seconds,
        language=get_settings().STT_LANGUAGE or "fa",
    )
    db.add(voice_note)
    db.flush()

    db.add(
        ClinicalEvent(
            patient=patient,
            event_type="voice_note_recorded",
            event_date=datetime.now(timezone.utc),
            title=f"ثبت یادداشت صوتی: {voice_note.title or 'بدون عنوان'}",
            source_type="voice_note",
            source_id=voice_note.id,
        )
    )
    db.commit()
    db.refresh(voice_note)

    # Persian speech-to-text runs after the response (ready-to-use model).
    background_tasks.add_task(process_voice_note, voice_note.id)
    return voice_note


@router.get(
    "/patients/{patient_id}/voice-notes",
    response_model=list[VoiceNoteResponse],
    summary="List a patient's voice notes",
    description="Newest first.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "بیمار یافت نشد"}},
)
def list_voice_notes(
    patient: Patient = Depends(patient_from_id),
    db: Session = Depends(get_db),
) -> list[VoiceNote]:
    voice_notes = db.scalars(
        select(VoiceNote)
        .where(VoiceNote.patient_id == patient.id)
        .order_by(VoiceNote.created_at.desc(), VoiceNote.id.desc())
    ).all()
    return list(voice_notes)


@router.get(
    "/voice-notes/{voice_note_id}",
    response_model=VoiceNoteResponse,
    summary="Get a voice note by id",
    responses={status.HTTP_404_NOT_FOUND: {"description": VOICE_NOTE_NOT_FOUND_DETAIL}},
)
def get_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceNote:
    return _get_voice_note_or_404(db, user, voice_note_id)


@router.get(
    "/voice-notes/{voice_note_id}/download",
    summary="Download the original audio",
    response_class=RedirectResponse,
    description="307 redirect to a short-lived presigned URL (audio is unchanged).",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": VOICE_NOTE_NOT_FOUND_DETAIL},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": STORAGE_UNAVAILABLE_DETAIL},
    },
)
def download_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    voice_note = _get_voice_note_or_404(db, user, voice_note_id)
    try:
        url = storage.presigned_download_url(voice_note.audio_storage_key)
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STORAGE_UNAVAILABLE_DETAIL,
        ) from None
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.patch(
    "/voice-notes/{voice_note_id}",
    response_model=VoiceNoteResponse,
    summary="Rename a voice note (title only)",
    description="The raw transcript is never edited in place.",
    responses={status.HTTP_404_NOT_FOUND: {"description": VOICE_NOTE_NOT_FOUND_DETAIL}},
)
def update_voice_note(
    voice_note_id: int,
    payload: VoiceNoteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceNote:
    voice_note = _get_voice_note_or_404(db, user, voice_note_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(voice_note, field, value)
    db.commit()
    db.refresh(voice_note)
    return voice_note


@router.post(
    "/voice-notes/{voice_note_id}/transcribe",
    response_model=VoiceNoteResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-run transcription",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": VOICE_NOTE_NOT_FOUND_DETAIL},
        status.HTTP_409_CONFLICT: {"description": TRANSCRIPTION_ALREADY_RUNNING_DETAIL},
    },
)
def retranscribe_voice_note(
    voice_note_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceNote:
    voice_note = _get_voice_note_or_404(db, user, voice_note_id)
    if voice_note.transcription_status == TranscriptionStatus.processing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=TRANSCRIPTION_ALREADY_RUNNING_DETAIL,
        )
    background_tasks.add_task(process_voice_note, voice_note.id)
    return voice_note


@router.post(
    "/voice-notes/{voice_note_id}/note",
    response_model=ClinicalNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save the reviewed transcript as a clinical note",
    description=(
        "The doctor reviews/edits the raw transcript and confirms it into "
        "the patient record. The note keeps a link to the original "
        "recording (`voice_note_id`) for traceability. This is the ONLY way "
        "transcript content becomes part of the record — never automatic."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": VOICE_NOTE_NOT_FOUND_DETAIL}},
)
def create_note_from_transcript(
    voice_note_id: int,
    payload: CreateNoteFromTranscript,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClinicalNote:
    voice_note = _get_voice_note_or_404(db, user, voice_note_id)
    note = ClinicalNote(
        patient_id=voice_note.patient_id,
        voice_note_id=voice_note.id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        source="voice",
    )
    db.add(note)
    db.flush()

    db.add(
        ClinicalEvent(
            patient_id=voice_note.patient_id,
            event_type="note_created",
            event_date=datetime.now(timezone.utc),
            title=f"ثبت یادداشت از روی یادداشت صوتی: {note.title}",
            source_type="clinical_note",
            source_id=note.id,
        )
    )
    db.commit()
    db.refresh(note)
    return note


@router.delete(
    "/voice-notes/{voice_note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a voice note",
    description="Removes the original audio, the row, and its timeline event. Clinical notes derived from it are kept (link set to null).",
    responses={status.HTTP_404_NOT_FOUND: {"description": VOICE_NOTE_NOT_FOUND_DETAIL}},
)
def delete_voice_note(
    voice_note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    voice_note = _get_voice_note_or_404(db, user, voice_note_id)
    try:
        storage.delete_object(voice_note.audio_storage_key)
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STORAGE_UNAVAILABLE_DETAIL,
        ) from None

    db.delete(voice_note)
    db.execute(
        delete(ClinicalEvent).where(
            ClinicalEvent.source_type == "voice_note",
            ClinicalEvent.source_id == voice_note_id,
        )
    )
    try:
        db.commit()
    except Exception:  # noqa: BLE001 — concurrent delete → same outcome
        db.rollback()
    return None
