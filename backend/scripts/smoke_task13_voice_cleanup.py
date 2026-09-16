"""Live smoke for Task 13: STT provider layer + optional AI cleanup.

Honest live run against the running backend:
- uploads a real (valid) WAV — a tone, NOT real Persian speech, so the
  transcript is expected to be empty/meaningless; the point is exercising
  the real Speechmatics job flow through the new provider class and the
  real cleanup behaviour (whatever it honestly is on this machine).
- never fakes results: every status is printed as the backend reports it.

Leaves the database clean (deletes the voice note and the test patient).
"""

import io
import math
import struct
import sys
import time
import wave

import httpx

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8003/api/v1"
client = httpx.Client(base_url=BASE, timeout=120)


def make_wav(seconds: float = 2.0, frequency: int = 440) -> bytes:
    """A real, valid WAV file (tone) with a proper RIFF header."""
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


# 1) throwaway patient
patient = client.post(
    "/patients",
    json={"first_name": "تست", "last_name": "تسک ۱۳ (smoke)"},
).json()
patient_id = patient["id"]
print(f"1) patient created: id={patient_id}")

try:
    # 2) upload real WAV → background STT (real Speechmatics) + optional cleanup
    audio = make_wav()
    upload = client.post(
        f"/patients/{patient_id}/voice-notes",
        files={"file": ("smoke.webm", audio, "audio/wav")},
        data={"title": "smoke تسک ۱۳", "duration_seconds": "2"},
    )
    assert upload.status_code == 201, upload.text
    vn = upload.json()
    vn_id = vn["id"]
    print(f"2) uploaded {len(audio)} bytes → voice_note={vn_id} "
          f"(transcription={vn['transcription_status']}, cleanup={vn['cleanup_status']})")

    # 3) poll to a terminal transcription state (real job; give it time)
    deadline = time.time() + 180
    while time.time() < deadline:
        vn = client.get(f"/voice-notes/{vn_id}").json()
        if vn["transcription_status"] in {"completed", "failed"}:
            break
        time.sleep(2)
    print(f"3) transcription terminal: {vn['transcription_status']}")
    print(f"   transcript={vn['transcript']!r}")
    if vn["error_message"]:
        print(f"   error_message={vn['error_message'][:200]!r}")

    # 4) cleanup runs right after transcription — give it a moment, then read
    time.sleep(5)
    vn = client.get(f"/voice-notes/{vn_id}").json()
    print(f"4) cleanup_status={vn['cleanup_status']} "
          f"cleaned_note={vn['cleaned_note']!r} processed_at={vn['processed_at']}")

    # 5) patient context carries it (Task 9 architecture, unchanged)
    context = client.get(f"/patients/{patient_id}/context").json()
    carried = context["voice_notes"][0]
    assert carried["id"] == vn_id
    print("5) patient context carries the voice note "
          f"(transcript={'yes' if carried['transcript'] else 'none'}, "
          f"cleaned_note={'yes' if carried['cleaned_note'] else 'none'})")

    # 6) original audio preserved (byte-identical roundtrip)
    download = client.get(f"/voice-notes/{vn_id}/download", follow_redirects=False)
    stored = httpx.get(download.headers["location"]).content
    print(f"6) original audio preserved: {stored == audio} ({len(stored)} bytes)")

finally:
    # cleanup — leave the database clean
    client.delete(f"/voice-notes/{vn_id}")
    client.delete(f"/patients/{patient_id}")
    print("7) cleanup done (voice note + patient deleted)")
