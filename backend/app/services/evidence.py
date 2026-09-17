"""Patient-record evidence / provenance layer (Task 16).

Makes AI answers traceable to the patient's REAL records:

- every item in the Task-9 patient context gets a stable evidence id
  derived from its actual database primary key (``MED-42``, ``LAB-31``, …)
- the AI is instructed to cite ONLY those ids; the backend never trusts
  the model — every returned id is validated against the ids actually
  supplied in the context (foreign / fabricated ids are silently dropped)
- document-backed evidence resolves to the real document row; the
  ORIGINAL file stays in object storage and is served through the
  EXISTING secure download endpoint (307 → short-lived presigned URL).
  The model never sees or produces URLs; temporary URLs are never
  persisted.

This is patient-record provenance ONLY — no external medical literature
citations, no RAG, no retrieval (explicitly out of scope).
"""

import json
import logging

from pydantic import BaseModel, Field

from app.services import ai
from app.services.ai_medication_safety import MEDICATION_SAFETY_CHAT_PROMPT

logger = logging.getLogger(__name__)

# Context section → (evidence-id prefix, source_type). These are exactly
# the sections Task 9 builds — nothing invented.
_SECTION_EVIDENCE = {
    "medications": ("MED", "medication"),
    "allergies": ("ALLERGY", "allergy"),
    "conditions": ("COND", "condition"),
    "lab_results": ("LAB", "lab"),
    "documents": ("DOC", "document"),
    "clinical_notes": ("NOTE", "clinical_note"),
    "voice_notes": ("VOICE", "voice_note"),
}

MAX_EVIDENCE_ITEMS = 10  # defensive cap on a single answer


class EvidenceItem(BaseModel):
    """One validated piece of patient-record evidence.

    ``document_id`` points at the ORIGINAL source document when a real
    relationship exists (a document itself, or a lab extracted from one) —
    never fabricated. No URLs live here: the frontend opens the file via
    the existing secure document download endpoint.
    """

    source_id: str = Field(description="شناسهٔ پایدار شواهد، مثال LAB-31")
    source_type: str = Field(description="نوع رکورد منبع")
    description: str = Field(description="توصیف خوانا از رکورد واقعی")
    document_id: int | None = Field(
        default=None, description="سند منبع اصلی (در صورت وجود رابطهٔ واقعی)"
    )


def _describe(source_type: str, item: dict) -> str:
    """Human-readable description built ONLY from the real record fields."""
    if source_type == "medication":
        medication = item.get("medication") or {}
        name = medication.get("name") or "?"
        return f"{name}{f' ({item['dosage']})' if item.get('dosage') else ''}"
    if source_type == "allergy":
        text = item.get("allergen") or "?"
        if item.get("severity"):
            text += f" — شدت: {item['severity']}"
        return text
    if source_type == "condition":
        return item.get("name") or "?"
    if source_type == "lab":
        text = f"{item.get('test_name') or '?'} = {item.get('value') or '?'}"
        if item.get("unit"):
            text += f" {item['unit']}"
        return text
    if source_type == "document":
        return item.get("title") or "سند"
    if source_type == "clinical_note":
        return item.get("title") or "یادداشت بالینی"
    if source_type == "voice_note":
        return item.get("title") or "یادداشت صوتی"
    return "?"


def _document_id_for(source_type: str, item: dict) -> int | None:
    """The original source document, only when the data model really links one."""
    if source_type == "document":
        return item.get("id")
    if source_type == "lab":
        return item.get("document_id")  # real FK in lab_results (SET NULL)
    return None


def build_evidence_index(context_dict: dict) -> dict[str, dict]:
    """Map every real context record to its evidence id → metadata.

    Works on the serialized Task-9 context (``PatientContextResponse.model_dump()``);
    ids come from the actual database primary keys — never random, never new.
    """
    index: dict[str, dict] = {}
    for section, (prefix, source_type) in _SECTION_EVIDENCE.items():
        for item in context_dict.get(section, []):
            record_id = item.get("id")
            if record_id is None:
                continue
            evidence_id = f"{prefix}-{record_id}"
            index[evidence_id] = {
                "source_type": source_type,
                "record_id": record_id,
                "description": _describe(source_type, item),
                "document_id": _document_id_for(source_type, item),
            }
    return index


def annotate_context(context_dict: dict) -> None:
    """Attach the evidence id to every item of a context dict (in place).

    ``ai.build_user_message`` then serializes them into the prompt, so the
    model sees ``"evidence_id": "MED-42"`` next to each record.
    """
    for section, (prefix, _source_type) in _SECTION_EVIDENCE.items():
        for item in context_dict.get(section, []):
            if item.get("id") is not None:
                item["evidence_id"] = f"{prefix}-{item['id']}"


# --- prompts (composed from the EXISTING Task-10/14 prompts — not rewritten) ---

_EVIDENCE_RULES = """

Evidence rules:
- The patient record below contains a stable evidence id for every item,
  e.g. [MED-42], [ALLERGY-8], [COND-17], [LAB-31], [DOC-123], [NOTE-45],
  [VOICE-9].
- When you make a patient-specific claim, cite the supporting evidence id(s).
- ONLY use evidence ids that appear in the supplied record.
- NEVER invent an id.
- NEVER output URLs, links, PubMed ids, article titles, authors, or
  guideline names — no external sources exist in this system.
- Patient evidence proves claims about THIS patient (e.g. «بیمار X مصرف
  می‌کند»). It does NOT prove general medical-knowledge claims (e.g.
  «X با Y تداخل دارد») — state those from general knowledge WITHOUT
  citing evidence.
- If the patient evidence is insufficient, say so explicitly.

Response format — ONLY a JSON object, no markdown fences, no extra text:
{"answer": "<Persian answer>", "evidence": ["<EVIDENCE-ID>", ...]}
`evidence` contains ONLY the ids you actually used; it may be an empty list.
"""

EVIDENCE_CHAT_SYSTEM_PROMPT = (
    ai.SYSTEM_PROMPT + "\n" + _EVIDENCE_RULES
)
EVIDENCE_SAFETY_SYSTEM_PROMPT = (
    MEDICATION_SAFETY_CHAT_PROMPT + "\n" + _EVIDENCE_RULES
)


# --- model-output parsing + validation (never trust the model) ---


def parse_evidence_answer(raw: str) -> tuple[str, list[str]]:
    """Extract (answer, evidence-ids) from a model response.

    Fence/prose-tolerant. If the response is not valid JSON, the raw text
    is kept as the answer with NO evidence — a usable answer is never
    thrown away, and nothing is ever fabricated.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1 :] if first_newline != -1 else ""
    cleaned = cleaned.replace("```", "")

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return raw.strip(), []  # prose fallback — no evidence

    try:
        data = json.loads(cleaned[start : end + 1])
    except ValueError:
        return raw.strip(), []

    if not isinstance(data, dict):
        return raw.strip(), []

    answer = data.get("answer")
    evidence = data.get("evidence", [])
    if not isinstance(answer, str) or not answer.strip():
        return raw.strip(), []
    if not isinstance(evidence, list):
        evidence = []
    ids = [
        item.strip()
        for item in evidence
        if isinstance(item, str) and item.strip()
    ]
    return answer.strip(), ids


def validate_evidence(
    model_ids: list[str], valid_index: dict[str, dict]
) -> list[EvidenceItem]:
    """Keep only evidence ids that exist in THIS patient's context.

    Foreign ids (another patient's records), fabricated ids, URLs, or
    citation-like strings are dropped and logged — they never reach the
    frontend and are never transformed into valid-looking sources.
    """
    items: list[EvidenceItem] = []
    dropped: list[str] = []
    for evidence_id in dict.fromkeys(model_ids):  # dedup, keep order
        if len(items) >= MAX_EVIDENCE_ITEMS:
            break
        record = valid_index.get(evidence_id)
        if record is None:
            dropped.append(evidence_id)
            continue
        items.append(
            EvidenceItem(
                source_id=evidence_id,
                source_type=record["source_type"],
                description=record["description"],
                document_id=record["document_id"],
            )
        )
    if dropped:
        logger.warning(
            "dropped invalid evidence ids (not in patient context): %s", dropped
        )
    return items
