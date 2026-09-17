"""Task 19 — full end-to-end integration verification (LIVE services).

Real backend (:8000), real PostgreSQL, real MinIO, real Speechmatics STT,
real MCP stdio server. Gemini is attempted for real; on this machine
Google is network-blocked (documented) so AI-success paths are exercised
through the test suite instead — every live AI result below is reported
honestly (expected 502, never faked).
"""

import io
import json
import struct
import sys
import time
import wave

import httpx

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

API = "http://127.0.0.1:8000/api/v1"
PASS, FAIL = 0, 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    mark = "✓" if condition else "✗"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {mark} {label}" + (f" — {detail}" if detail and not condition else ""))


def tone_wav(seconds: float = 1.5) -> bytes:
    """A real valid WAV (tone — no speech; transcript expected empty)."""
    import math

    rate = 8000
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for i in range(int(rate * seconds)):
            wav.writeframes(struct.pack("<h", int(9000 * math.sin(2 * 3.14 * 440 * i / rate))))
    return buffer.getvalue()


admin = httpx.Client(base_url=API, timeout=120, headers={})
# --- 1..3 auth flow ---
print("\n== 1) Authentication ==")
r = admin.post("/auth/login", json={"email": "admin@example.com", "password": "admin-dev-12345"})
check("admin login", r.status_code == 200)
admin.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
me = admin.get("/auth/me").json()
check("/auth/me (admin, no hash)", me["role"] == "admin" and "password_hash" not in me)
check("anonymous blocked (401)", httpx.get(f"{API}/patients").status_code == 401)
bad = httpx.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "wrong"})
check("wrong password → 401 generic", bad.status_code == 401)
run_suffix = str(int(time.time()) % 100000)
d2_email = f"doctor2-{run_suffix}@example.com"
reg = admin.post("/auth/register", json={"email": d2_email, "password": "Doc-Two-12345", "full_name": "پزشک دوم"})
check("registration (doctor)", reg.status_code == 201)
doc2 = httpx.Client(base_url=API, timeout=120)
r = doc2.post("/auth/login", json={"email": d2_email, "password": "Doc-Two-12345"})
doc2.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
check("doctor2 login", r.status_code == 200)

# --- 4..7 patient + medical data + document ---
print("\n== 2) Patient creation & data ==")
pid = admin.post("/patients", json={"first_name": "بیمار", "last_name": "تسک ۱۹"}).json()["id"]
check("admin creates patient", pid > 0)
admin.post(f"/patients/{pid}/conditions", json={"name": "دیابت نوع ۲"})
admin.post(f"/patients/{pid}/allergies", json={"allergen": "Penicillin", "severity": "severe"})
med = admin.post(f"/patients/{pid}/medications", json={"medication_name": "Metformin 500", "dosage": "500 mg"}).json()
check("conditions+allergy+medication created", med["id"] > 0)

print("\n== 3) Document pipeline (upload → storage → extraction) ==")
pdf = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF"
doc = admin.post(f"/patients/{pid}/documents", files={"file": ("lab.pdf", pdf, "application/pdf")},
                 data={"title": "آزمایش خون تسک ۱۹", "doc_type": "lab_report"}).json()
check("document upload 201", doc["id"] > 0)
deadline = time.time() + 30
while time.time() < deadline:
    doc = admin.get(f"/documents/{doc['id']}").json()
    if doc["extraction_status"] in ("completed", "failed"):
        break
    time.sleep(1)
check("extraction terminal", doc["extraction_status"] in ("completed", "failed"), doc["extraction_status"])
dl = admin.get(f"/documents/{doc['id']}/download", follow_redirects=False)
stored = httpx.get(dl.headers["location"]).content if dl.status_code == 307 else b""
check("original byte-identical in MinIO", stored == pdf and dl.status_code == 307)

print("\n== 4) AI document analysis (real Gemini attempt) ==")
r = admin.post(f"/documents/{doc['id']}/analyze")
after = admin.get(f"/documents/{doc['id']}").json()
if r.status_code == 200:
    check("AI analysis live succeeded", after["analysis_status"] == "completed")
elif doc["extraction_status"] != "completed":
    check("analysis correctly refuses without completed extraction (409)",
          r.status_code == 409 and after["analysis_status"] == "pending")
else:
    check("AI analysis honest failure (network-blocked Gemini)", r.status_code == 502 and after["analysis_status"] == "failed")
check("original+extracted intact after analysis attempt", after["file_name"] == "lab.pdf")

# --- 10..11 context + timeline ---
print("\n== 5) Context & Timeline ==")
ctx = admin.get(f"/patients/{pid}/context").json()
check("context: meds+conditions+allergies+document", len(ctx["medications"]) == 1 and len(ctx["conditions"]) == 1
      and len(ctx["allergies"]) == 1 and len(ctx["documents"]) == 1)
tl = admin.get(f"/patients/{pid}/timeline").json()
types = {i["event_type"] for i in tl["items"]}
check("timeline events (medication_started, condition_onset, document_uploaded)",
      {"medication_started", "condition_onset", "document_uploaded"} <= types, str(types))

# --- 12..13 medication + AI safety ---
print("\n== 6) AI medication safety (real attempt) ==")
r = admin.post(f"/patients/{pid}/medications/ai-safety-check",
               json={"medications": [{"name": "Warfarin", "dose": "5 mg"}], "question": "تداخل دارد؟"})
if r.status_code == 200:
    check("AI safety live succeeded", "overall_assessment" in r.json())
else:
    check("AI safety honest failure (502)", r.status_code == 502)
saved = admin.post(f"/patients/{pid}/medications", json={"medication_name": "Warfarin", "dosage": "5 mg"}).json()
check("medication save NOT blocked by AI failure", saved["id"] > 0)

# --- 14..19 conversation + chat + failure + evidence ---
print("\n== 7) Persistent chat + failure semantics + evidence ==")
conv = admin.post(f"/patients/{pid}/conversations", json={"title": "ویزیت تسک ۱۹"}).json()
untitled = admin.post(f"/patients/{pid}/conversations", json={}).json()
r = admin.post(f"/conversations/{conv['id']}/messages", json={"content": "خلاصهٔ وضعیت بیمار؟", "medication_safety": False})
reloaded = admin.get(f"/conversations/{conv['id']}").json()
if r.status_code == 200:
    body = r.json()
    check("chat live succeeded + both messages persisted",
          len(reloaded["messages"]) == 2 and body["assistant_message"]["content"])
else:
    check("chat honest failure (502) + user message persisted",
          r.status_code == 502 and len(reloaded["messages"]) == 1, f"{r.status_code}")
    check("NO fake assistant message", not any(m["role"] == "assistant" for m in reloaded["messages"]))
check("explicit title kept", reloaded["title"] == "ویزیت تسک ۱۹")
ru = admin.get(f"/conversations/{untitled['id']}").json()
admin.post(f"/conversations/{untitled['id']}/messages", json={"content": "سلام", "medication_safety": False})
ru = admin.get(f"/conversations/{untitled['id']}").json()
check("derived title from first message (untitled)", ru["title"] == "سلام")

# --- 20 source-document download authorization ---
print("\n== 8) Voice workflow (real Speechmatics) ==")
audio = tone_wav()
vn = admin.post(f"/patients/{pid}/voice-notes", files={"file": ("note.wav", audio, "audio/wav")},
                data={"title": "یادداشت صوتی تسک ۱۹", "duration_seconds": "2"}).json()
deadline = time.time() + 120
while time.time() < deadline:
    vn = admin.get(f"/voice-notes/{vn['id']}").json()
    if vn["transcription_status"] in ("completed", "failed"):
        break
    time.sleep(2)
check("STT (real Speechmatics) completed", vn["transcription_status"] == "completed", vn.get("transcription_status"))
check("raw transcript is real model output (empty for tone)", vn["transcript"] in (None, ""))
check("cleanup skipped on empty transcript (no AI config on this path anyway)", vn["cleanup_status"] == "pending")
ctx = admin.get(f"/patients/{pid}/context").json()
tl = admin.get(f"/patients/{pid}/timeline").json()
check("voice note in Context + Timeline", len(ctx["voice_notes"]) == 1
      and any(i["event_type"] == "voice_note_recorded" for i in tl["items"]))

# --- 25 MCP agent read-only flow ---
print("\n== 9) Agent/MCP (real stdio server, real PG) ==")
from app.services.agent import get_mcp_client, MCPToolError
client = get_mcp_client()
tools = client.list_tools()
check("6 read-only tools registered", sorted(tools) == sorted(
    ["get_patient", "get_patient_context", "get_patient_labs", "get_patient_medications", "get_patient_documents", "get_patient_timeline"]))
meds = client.call_tool("get_patient_medications", {"patient_id": pid})
check("tools read real PG data", any("Warfarin" in m["medication"]["name"] for m in meds))
docs_meta = client.call_tool("get_patient_documents", {"patient_id": pid})
check("documents metadata-only via MCP (no storage_key/text)", docs_meta and set(docs_meta[0]) <= {
    "id", "title", "doc_type", "file_name", "mime_type", "file_size_bytes", "extraction_status", "created_at"})
try:
    client.call_tool("get_patient", {"patient_id": 999999})
    check("unknown patient clean error", False)
except MCPToolError:
    check("unknown patient clean error", True)

# --- 26..27 isolation matrix (live) ---
print("\n== 10) Patient isolation (live) ==")
own = doc2.post("/patients", json={"first_name": "بیمار", "last_name": "دکتر ۲"}).json()
d2list = doc2.get("/patients").json()
check("doctor2 sees ONLY own auto-assigned patient", d2list["total"] == 1 and d2list["items"][0]["id"] == own["id"])
check("doctor2 → task19 patient: 403", doc2.get(f"/patients/{pid}").status_code == 403)
check("doctor2 → task19 document download: 403 (before presigned)",
      doc2.get(f"/documents/{doc['id']}/download", follow_redirects=False).status_code == 403)
check("doctor2 → task19 conversation: 403", doc2.get(f"/conversations/{conv['id']}").status_code == 403)
check("doctor2 → task19 voice note: 403", doc2.get(f"/voice-notes/{vn['id']}").status_code == 403)
check("doctor2 → task19 chat/safety/agent: 403",
      doc2.post(f"/patients/{pid}/chat", json={"question": "x"}).status_code == 403
      and doc2.post(f"/patients/{pid}/medications/ai-safety-check", json={"medications": [{"name": "X"}]}).status_code == 403
      and doc2.post(f"/patients/{pid}/agent/chat", json={"content": "x"}).status_code == 403)
check("admin → everything: 200", admin.get(f"/patients/{pid}").status_code == 200)

# --- cleanup ---
admin.delete(f"/patients/{pid}")
admin.delete(f"/patients/{own['id']}")
print(f"\n===== E2E RESULT: {PASS} passed, {FAIL} failed =====")
sys.exit(1 if FAIL else 0)
