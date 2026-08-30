"""Reproduce the reported 422 and verify the fixed multipart wire format.

Simulates exactly what the browser sends for BOTH upload paths:
1. the BUGGY old request: FormData body + forced Content-Type application/json
2. the FIXED recorded-audio request (MediaRecorder → webm, boundary auto)
3. the FIXED selected-file request (e.g. mp3 from the file picker)
"""

import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

BASE = "http://127.0.0.1:8000/api/v1"
client = httpx.Client(base_url=BASE, timeout=60)

patient_id = client.get("/patients").json()["items"][0]["id"]
print(f"patient id: {patient_id}")

FAKE_WEBM = b"\x1a\x45\xdf\xa3EBML-fake-recorded-audio-body"
FAKE_MP3 = b"\xff\xfb\x90\x00fake-mp3-selected-file-body"

created_ids = []

# 1) reproduce the bug: multipart body + manual application/json Content-Type
buggy = httpx.post(
    f"{BASE}/patients/{patient_id}/voice-notes",
    content=(
        b"--X\r\nContent-Disposition: form-data; name=\"file\"; "
        b"filename=\"r.webm\"\r\nContent-Type: audio/webm\r\n\r\n" + FAKE_WEBM + b"\r\n--X--\r\n"
    ),
    headers={"Content-Type": "application/json"},  # what the old request() did
)
print(f"1) BUGGY (forced application/json): HTTP {buggy.status_code}")
if buggy.status_code == 422:
    detail = buggy.json().get("detail")
    print("   body:", [e.get("loc") for e in detail])

# 2) fixed: recorded audio (MediaRecorder webm) — FormData, no manual content-type
fixed_recording = client.post(
    f"/patients/{patient_id}/voice-notes",
    files={"file": ("recording.webm", FAKE_WEBM, "audio/webm")},
    data={"title": "ضبط میکروفون", "conversation_type": "physician_note", "duration_seconds": "5"},
)
print(f"2) RECORDED (webm, auto boundary): HTTP {fixed_recording.status_code}")
assert fixed_recording.status_code == 201, fixed_recording.text
rec = fixed_recording.json()
assert rec["duration_seconds"] == 5 and rec["language"] == "fa"
created_ids.append(rec["id"])

# 2b) codecs-parameter variant (what MediaRecorder reports before cleanup)
with_codecs = client.post(
    f"/patients/{patient_id}/voice-notes",
    files={"file": ("recording.webm", FAKE_WEBM, "audio/webm;codecs=opus")},
)
print(f"2b) webm with ';codecs=opus' part type: HTTP {with_codecs.status_code}")
assert with_codecs.status_code == 201, with_codecs.text
created_ids.append(with_codecs.json()["id"])

# 3) fixed: selected file from the picker (mp3)
selected = client.post(
    f"/patients/{patient_id}/voice-notes",
    files={"file": ("song-note.mp3", FAKE_MP3, "audio/mpeg")},
    data={"title": "فایل انتخابی", "conversation_type": "doctor_patient"},
)
print(f"3) SELECTED FILE (mp3): HTTP {selected.status_code}")
assert selected.status_code == 201, selected.text
assert selected.json()["conversation_type"] == "doctor_patient"
created_ids.append(selected.json()["id"])

# cleanup
for vn_id in created_ids:
    assert client.delete(f"/voice-notes/{vn_id}").status_code == 204
print(f"cleanup: {len(created_ids)} test voice notes removed")

print("\nWIRE-FORMAT VERIFICATION PASSED")
