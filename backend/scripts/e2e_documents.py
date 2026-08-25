"""One-off E2E verification for Task 6 (documents API + MinIO). Not a test file."""

import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")  # Windows console + Persian output

BASE = "http://127.0.0.1:8000/api/v1"
PDF = b"%PDF-1.7\nfake clinical pdf for e2e\n%%EOF"

client = httpx.Client(base_url=BASE, timeout=30)

# 0) find a patient
patients = client.get("/patients").json()["items"]
assert patients, "no patients — seed first"
patient_id = patients[0]["id"]
print(f"patient: {patients[0]['first_name']} (id={patient_id})")

# 1) upload (multipart with Persian title)
response = client.post(
    f"/patients/{patient_id}/documents",
    files={"file": ("lab-report.pdf", PDF, "application/pdf")},
    data={"title": "آزمایش خون — تست زنده", "doc_type": "lab_report"},
)
assert response.status_code == 201, response.text
doc = response.json()
doc_id = doc["id"]
print("1) upload 201:", doc["title"], "|", doc["mime_type"], "|", doc["file_size_bytes"], "bytes |", doc["extraction_status"])
assert "storage_key" not in doc

# 2) list contains the new document
listing = client.get(f"/patients/{patient_id}/documents").json()
assert any(item["id"] == doc_id for item in listing)
print(f"2) list: {len(listing)} documents, new doc present, newest-first ids:", [i["id"] for i in listing][:3])

# 3) download → 307 → fetch original bytes from MinIO
redirect = client.get(f"/documents/{doc_id}/download", follow_redirects=False)
assert redirect.status_code == 307, redirect.text
presigned = redirect.headers["location"]
with httpx.Client(timeout=30) as raw:
    downloaded = raw.get(presigned)
assert downloaded.status_code == 200 and downloaded.content == PDF
print(f"3) download: 307 → presigned ({presigned.split('?')[0]}) → byte-identical roundtrip ✓")

# 4) timeline event created
import psycopg2  # noqa: E402

from app.core.config import get_settings  # noqa: E402

_settings = get_settings()


def _db_connection():
    return psycopg2.connect(
        host=_settings.POSTGRES_HOST,
        port=_settings.POSTGRES_PORT,
        user=_settings.POSTGRES_USER,
        password=_settings.POSTGRES_PASSWORD,
        dbname=_settings.POSTGRES_DB,
    )


conn = _db_connection()
with conn, conn.cursor() as cur:
    cur.execute(
        "SELECT event_type, title FROM clinical_events WHERE source_type='document' AND source_id=%s",
        (doc_id,),
    )
    events = cur.fetchall()
conn.close()
assert len(events) == 1 and events[0][0] == "document_uploaded"
print(f"4) timeline event: {events[0][0]} — {events[0][1]}")

# 5) PATCH metadata
patched = client.patch(f"/documents/{doc_id}", json={"title": "آزمایش خون — اصلاح‌شده"})
assert patched.status_code == 200 and patched.json()["title"] == "آزمایش خون — اصلاح‌شده"
assert patched.json()["file_name"] == "lab-report.pdf"
print("5) patch: title updated, file untouched ✓")

# 6) invalid type rejected (nothing stored)
before = len(client.get(f"/patients/{patient_id}/documents").json())
bad = client.post(
    f"/patients/{patient_id}/documents",
    files={"file": ("malware.exe", b"MZ..", "application/x-msdownload")},
)
assert bad.status_code == 422, bad.text
assert len(client.get(f"/patients/{patient_id}/documents").json()) == before
print("6) invalid mime → 422, nothing stored ✓")

# 7) DELETE → metadata + object + event removed
assert client.delete(f"/documents/{doc_id}").status_code == 204
assert client.get(f"/documents/{doc_id}").status_code == 404
with httpx.Client(timeout=30) as raw:
    assert raw.get(presigned).status_code in (403, 404), "object should be gone from MinIO"
conn = _db_connection()
with conn, conn.cursor() as cur:
    cur.execute(
        "SELECT count(*) FROM clinical_events WHERE source_type='document' AND source_id=%s",
        (doc_id,),
    )
    (count,) = cur.fetchone()
conn.close()
assert count == 0
print("7) delete: metadata gone, MinIO object gone, timeline event gone ✓")

# 8) errors: missing patient, missing document
assert client.post("/patients/999999/documents", files={"file": ("a.pdf", PDF, "application/pdf")}).status_code == 404
assert client.get("/documents/999999").status_code == 404
print("8) 404s with Persian details:",
      client.get("/documents/999999").json()["detail"])

print("\nE2E: ALL CHECKS PASSED")
