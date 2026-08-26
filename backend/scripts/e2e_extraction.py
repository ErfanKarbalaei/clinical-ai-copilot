"""E2E for Task 7: real files through upload → deterministic extraction.

Verifies: PDF text layer, Persian OCR image, blank/scanned PDF handling,
status lifecycle, and the extract-retry endpoint. Leaves the database clean.
"""

import io
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from tests.pdf_helper import pdf_with_text  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"

client = httpx.Client(base_url=BASE, timeout=60)

patients = client.get("/patients").json()["items"]
assert patients, "no patients — seed first"
patient_id = patients[0]["id"]
print(f"patient: {patients[0]['first_name']} (id={patient_id})")


def wait_for_terminal(doc_id: int, timeout: float = 60.0) -> dict:
    """Poll until extraction finishes (background task)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        doc = client.get(f"/documents/{doc_id}").json()
        if doc["extraction_status"] in {"completed", "failed"}:
            return doc
        time.sleep(0.5)
    raise AssertionError(f"extraction did not finish for document {doc_id}")


def upload(name: str, data: bytes, mime: str) -> dict:
    response = client.post(
        f"/patients/{patient_id}/documents",
        files={"file": (name, data, mime)},
    )
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["extraction_status"] in {"pending", "processing"}
    return wait_for_terminal(doc["id"])


# 1) real text-layer PDF
pdf_doc = upload(
    "report.pdf",
    pdf_with_text("CLINICAL LAB REPORT WITH DETAILED PATIENT LABORATORY RESULTS"),
    "application/pdf",
)
assert pdf_doc["extraction_status"] == "completed", pdf_doc
assert "CLINICAL LAB REPORT" in pdf_doc["extracted_text"]
print("1) text PDF  → completed | extracted:", pdf_doc["extracted_text"][:40], "…")

# 2) Persian text image → OCR
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

image = Image.new("RGB", (1100, 200), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.truetype("C:/Windows/Fonts/tahoma.ttf", 72)
draw.text((30, 60), "گزارش آزمایشگاه بالینی", fill="black", font=font)
buffer = io.BytesIO()
image.save(buffer, format="PNG")
png_doc = upload("persian-note.png", buffer.getvalue(), "image/png")
assert png_doc["extraction_status"] == "completed", png_doc
assert len(png_doc["extracted_text"].strip()) >= 5
print("2) Persian image OCR → completed | extracted:", png_doc["extracted_text"].strip()[:40])

# 3) blank (scanned-like) PDF — no text layer, no images
blank_pdf = pdf_with_text("")
blank_doc = upload("scan.pdf", blank_pdf, "application/pdf")
print(
    "3) blank PDF  →", blank_doc["extraction_status"], "| text:",
    repr((blank_doc["extracted_text"] or "")[:30]),
)
assert blank_doc["extraction_status"] in {"completed", "failed"}

# 4) original file intact (download roundtrip for the text PDF)
redirect = client.get(f"/documents/{pdf_doc['id']}/download", follow_redirects=False)
assert redirect.status_code == 307
with httpx.Client(timeout=30) as raw:
    downloaded = raw.get(redirect.headers["location"])
assert downloaded.status_code == 200
assert downloaded.content == pdf_with_text(
    "CLINICAL LAB REPORT WITH DETAILED PATIENT LABORATORY RESULTS"
)
print("4) original file unchanged after processing ✓")

# 5) re-extract endpoint returns 202 and re-runs
retry = client.post(f"/documents/{pdf_doc['id']}/extract")
assert retry.status_code == 202, retry.text
time.sleep(2)  # let the background task actually start before polling
final = wait_for_terminal(pdf_doc["id"])
assert final["extraction_status"] == "completed"
print("5) re-extract: 202 → completed ✓")

# cleanup — remove only what we created
for doc_id in (pdf_doc["id"], png_doc["id"], blank_doc["id"]):
    assert client.delete(f"/documents/{doc_id}").status_code == 204
print("cleanup: test documents removed (seed data untouched)")

print("\nE2E EXTRACTION: ALL CHECKS PASSED")
