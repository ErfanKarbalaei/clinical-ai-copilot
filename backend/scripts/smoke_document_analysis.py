"""Live smoke for Task 12: upload → deterministic extraction → AI analysis."""
import sys, time
import httpx

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8003/api/v1"
client = httpx.Client(base_url=BASE, timeout=120)

patients = client.get("/patients").json()["items"]
pid = patients[0]["id"]
print(f"patient: {patients[0]['first_name']} (id={pid})")

# 1) upload a text document (deterministic extraction completes fast)
LAB_TEXT = ("CLINICAL LAB REPORT\nHbA1c: 8.2 %\nFBS: 168 mg/dL\nLDL: 140 mg/dL\n"
            "Patient on metformin and losartan.")
upload = client.post(
    f"/patients/{pid}/documents",
    files={"file": ("lab-note.txt", LAB_TEXT.encode(), "text/plain")},
    data={"title": "آزمایش خون — تحلیل", "doc_type": "lab_report"},
)
assert upload.status_code == 201, upload.text
doc_id = upload.json()["id"]
print("1) upload 201 | extraction_status:", upload.json()["extraction_status"],
      "| analysis_status:", upload.json()["analysis_status"])

for _ in range(20):
    doc = client.get(f"/documents/{doc_id}").json()
    if doc["extraction_status"] in {"completed", "failed"}:
        break
    time.sleep(0.5)
print("2) extraction →", doc["extraction_status"], "| text ok:",
      "HbA1c" in (doc["extracted_text"] or ""))

# 3) analyze on a pending-extraction document first (409 path)
pending = client.post(
    f"/patients/{pid}/documents",
    files={"file": ("img.png", b"\x89PNG-fake-not-ocrable", "image/png")},
)
pid_doc = pending.json()["id"]
time.sleep(2)
pdoc = client.get(f"/documents/{pid_doc}").json()
conflict = client.post(f"/documents/{pid_doc}/analyze")
print("3) analyze before extraction:", pdoc["extraction_status"], "→ HTTP",
      conflict.status_code, "|", conflict.json().get("detail", "")[:60])

# 4) analyze the extracted document with the REAL provider
analysis = client.post(f"/documents/{doc_id}/analyze")
print("4) analyze (real provider) → HTTP", analysis.status_code)
if analysis.status_code == 200:
    body = analysis.json()
    print("   analysis_status:", body["analysis_status"])
    print("   ai_summary:", (body["ai_summary"] or "")[:200])
else:
    print("   detail:", analysis.json().get("detail"))
    doc = client.get(f"/documents/{doc_id}").json()
    print("   persisted analysis_status:", doc["analysis_status"],
          "| extracted_text intact:", "HbA1c" in (doc["extracted_text"] or ""))

# 5) cleanup
for did in (doc_id, pid_doc):
    assert client.delete(f"/documents/{did}").status_code == 204
print("5) cleanup ✓")
print("\nSMOKE DONE")
