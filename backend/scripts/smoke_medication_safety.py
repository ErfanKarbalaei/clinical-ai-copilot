"""Live smoke test for the medication-safety endpoint (Task 11)."""

import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8003/api/v1"
client = httpx.Client(base_url=BASE, timeout=60)

patients = client.get("/patients").json()["items"]
assert patients, "no patients — seed first"
patient = patients[0]  # seed order: علی (metformin + losartan, penicillin allergy)
pid = patient["id"]
print(f"patient: {patient['first_name']} (id={pid})")

# 1) NSAID candidate → interaction with Losartan (INT-005)
response = client.post(f"/patients/{pid}/medications/check", json={"medication_name": "Ibuprofen 400"})
assert response.status_code == 200, response.text
body = response.json()
print("1) Ibuprofen 400 → covered:", body["candidate_covered"],
      "| classes:", body["candidate_class_labels"], "| rules:", body["rules_version"])
for w in body["warnings"]:
    print(f"   [{w['severity']}] {w['warning_type']} {w['rule_id']}: {w['title']} | involved={w['involved']}")
assert any(w["rule_id"] == "INT-005" for w in body["warnings"])

# 2) Amoxicillin → severe same-class allergy (XALL-000)
body = client.post(f"/patients/{pid}/medications/check", json={"medication_name": "Amoxicillin 500"}).json()
print("2) Amoxicillin 500 →")
for w in body["warnings"]:
    print(f"   [{w['severity']}] {w['rule_id']}: {w['title']}")
assert any(w["rule_id"] == "XALL-000" and w["severity"] == "severe" for w in body["warnings"])

# 3) duplicate therapy (Metformin already active)
body = client.post(f"/patients/{pid}/medications/check", json={"medication_name": "Metformin 850"}).json()
print("3) Metformin 850 →")
for w in body["warnings"]:
    print(f"   [{w['severity']}] {w['rule_id']}: {w['title']} | involved={w['involved']}")
assert any(w["warning_type"] == "duplicate_therapy" for w in body["warnings"])

# 4) explain=true with the real (currently network-blocked) provider
response = client.post(
    f"/patients/{pid}/medications/check",
    json={"medication_name": "Ibuprofen 400", "explain": True},
)
assert response.status_code == 200, response.text
body = response.json()
print("4) explain=true → HTTP 200 | warnings intact:",
      [w["rule_id"] for w in body["warnings"]], "| explanation:", body["explanation"])

# 5) validations / 404s
assert client.post(f"/patients/{pid}/medications/check", json={"dosage": "x"}).status_code == 422
assert client.post(f"/patients/{pid}/medications/check", json={"medication_id": 999999}).status_code == 404
assert client.post("/patients/999999/medications/check", json={"medication_name": "x"}).status_code == 404
print("5) 422 (no candidate) / 404 (unknown drug id) / 404 (unknown patient) ✓")

# 6) chat (Task 10) untouched — returns 503/502/200 depending on provider, not 500
chat = client.post(f"/patients/{pid}/chat", json={"question": "وضعیت؟"})
print("6) chat endpoint still responds:", chat.status_code)
assert chat.status_code in (200, 502, 503)

print("\nSMOKE: ALL CHECKS PASSED")
