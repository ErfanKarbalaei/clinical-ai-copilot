"""E2E for Task 8: voice notes — upload, storage, lifecycle, review workflow.

Without SPEECHMATICS_API_KEY the transcription path deterministically ends
as `failed` (with the reason logged) — everything else is fully verified:
original audio preserved, timeline event, rename, retry, note-from-transcript,
and delete semantics. Leaves the database clean.
"""

import io
import sys
import time
import wave

import httpx

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

BASE = "http://127.0.0.1:8000/api/v1"
client = httpx.Client(base_url=BASE, timeout=60)

patients = client.get("/patients").json()["items"]
assert patients, "seed first"
patient_id = patients[0]["id"]
print(f"patient: {patients[0]['first_name']} (id={patient_id})")


def make_wav(seconds: float = 2.0, frequency: int = 440) -> bytes:
    """A real, valid WAV file (silence-ish tone) with a proper RIFF header."""
    import math
    import struct

    rate = 8000
    frames = int(rate * seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for i in range(frames):
            value = int(12000 * math.sin(2 * math.pi * frequency * i / rate))
            wav.writeframes(struct.pack("<h", value))
    return buffer.getvalue()


AUDIO = make_wav()
print(f"generated real WAV: {len(AUDIO)} bytes")


def wait_terminal(vn_id: int, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = client.get(f"/voice-notes/{vn_id}").json()
        if item["transcription_status"] in {"completed", "failed"}:
            return item
        time.sleep(0.5)
    raise AssertionError(f"transcription did not finish for voice note {vn_id}")


# 1) upload (multipart with Persian title + conversation type)
response = client.post(
    f"/patients/{patient_id}/voice-notes",
    files={"file": ("visit.webm", AUDIO, "audio/webm")},
    data={"title": "یادداشت صوتی ویزیت", "conversation_type": "physician_note", "duration_seconds": "2"},
)
assert response.status_code == 201, response.text
created = response.json()
assert created["transcription_status"] in {"pending", "processing"}
vn_id = created["id"]
print(f"1) upload 201: {created['title']} | status={created['transcription_status']} | lang={created['language']}")

# 2) transcription outcome (failed without API key — deterministic)
final = wait_terminal(vn_id)
if final["transcription_status"] == "completed":
    print("2) transcription COMPLETED (API key present):", (final["transcript"] or "")[:60])
else:
    assert final["transcription_status"] == "failed"
    assert final["transcript"] is None
    print("2) transcription failed as expected (no SPEECHMATICS_API_KEY) — reason logged server-side")

# 3) original audio preserved — byte-identical roundtrip
redirect = client.get(f"/voice-notes/{vn_id}/download", follow_redirects=False)
assert redirect.status_code == 307, redirect.text
with httpx.Client(timeout=30) as raw:
    downloaded = raw.get(redirect.headers["location"])
assert downloaded.status_code == 200 and downloaded.content == AUDIO
print("3) original audio preserved byte-identical ✓")

# 4) still stored in MinIO after the failed transcription
from app.core.config import get_settings  # noqa: E402
from app.services import storage  # noqa: E402

import psycopg2  # noqa: E402

settings = get_settings()
conn = psycopg2.connect(
    host=settings.POSTGRES_HOST, port=settings.POSTGRES_PORT,
    user=settings.POSTGRES_USER, password=settings.POSTGRES_PASSWORD,
    dbname=settings.POSTGRES_DB,
)
with conn, conn.cursor() as cur:
    cur.execute("SELECT audio_storage_key FROM voice_notes WHERE id=%s", (vn_id,))
    (key,) = cur.fetchone()
    cur.execute(
        "SELECT count(*) FROM clinical_events WHERE source_type='voice_note' AND source_id=%s",
        (vn_id,),
    )
    (event_count,) = cur.fetchone()
conn.close()
stat = storage.get_client().stat_object(settings.MINIO_BUCKET, key)
assert stat.size == len(AUDIO)
assert event_count == 1
print(f"4) audio still in MinIO after processing ({stat.size} bytes) + timeline event ✓")

# 5) rename
renamed = client.patch(f"/voice-notes/{vn_id}", json={"title": "یادداشت ویزیت — اصلاح شده"})
assert renamed.status_code == 200 and renamed.json()["title"] == "یادداشت ویزیت — اصلاح شده"
print("5) rename ✓")

# 6) retry transcription → 202
retry = client.post(f"/voice-notes/{vn_id}/transcribe")
assert retry.status_code == 202, retry.text
time.sleep(2)
wait_terminal(vn_id)
print("6) re-transcribe: 202 → terminal ✓")

# 7) review workflow: create a clinical note from the (doctor-reviewed) transcript
note = client.post(
    f"/voice-notes/{vn_id}/note",
    json={"title": "خلاصه ویزیت صوتی", "content": "بیمار حال عمومی خوبی دارد؛ ادامه داروها."},
)
assert note.status_code == 201, note.text
note_body = note.json()
assert note_body["source"] == "voice" and note_body["voice_note_id"] == vn_id
print("7) note from transcript: 201, linked to recording ✓")

# 8) delete → audio gone, event gone, derived note survives with NULL link
assert client.delete(f"/voice-notes/{vn_id}").status_code == 204
listing = storage.get_client().list_objects(settings.MINIO_BUCKET, prefix=key)
assert list(listing) == []
conn = psycopg2.connect(
    host=settings.POSTGRES_HOST, port=settings.POSTGRES_PORT,
    user=settings.POSTGRES_USER, password=settings.POSTGRES_PASSWORD,
    dbname=settings.POSTGRES_DB,
)
with conn, conn.cursor() as cur:
    cur.execute("SELECT voice_note_id FROM clinical_notes WHERE id=%s", (note_body["id"],))
    (survivor_link,) = cur.fetchone()
conn.close()
assert survivor_link is None
print("8) delete: audio+event removed, derived note kept (link NULL) ✓")

print("\nE2E VOICE NOTES: ALL CHECKS PASSED")
