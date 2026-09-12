"""Deterministic medication-safety rule engine (prescription safety).

Per the project architecture (spec §11):

    Medication → rule / knowledge base → deterministic safety result
              → (optional) LLM explanation

Warnings are produced ONLY by this engine against a versioned local rules
knowledge base (``app/data/medication_rules.json``). An LLM may later explain
the warnings in Persian, but it can never invent, alter, or suppress one.
Pure functions, no database access, no network — fully unit-testable.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from app.schemas.medication_safety import SafetyWarning

RULES_FILE = Path(__file__).resolve().parent.parent / "data" / "medication_rules.json"

# Same-class allergy conflict when no specific cross-reactivity rule applies.
SAME_CLASS_ALLERGY_RULE_ID = "XALL-000"
DUPLICATE_THERAPY_RULE_ID = "DUP-000"

SEVERITY_ORDER = {"mild": 0, "moderate": 1, "severe": 2}


@dataclass(frozen=True)
class DrugClass:
    id: str
    label_en: str
    label_fa: str
    aliases: tuple[str, ...]
    duplicate_allowed: bool = False


@dataclass(frozen=True)
class InteractionRule:
    rule_id: str
    classes: frozenset[str]
    severity: str
    title_fa: str
    detail_fa: str


@dataclass(frozen=True)
class CrossReactivityRule:
    rule_id: str
    allergen_class: str
    candidate_class: str
    severity: str
    title_fa: str
    detail_fa: str


@dataclass(frozen=True)
class RulesKB:
    version: str
    source_note: str
    classes: dict[str, DrugClass]
    interactions: tuple[InteractionRule, ...]
    cross_reactivity: tuple[CrossReactivityRule, ...]


@lru_cache(maxsize=1)
def load_rules_kb() -> RulesKB:
    """Load and index the rules knowledge base (cached per process)."""
    payload = json.loads(RULES_FILE.read_text(encoding="utf-8"))

    classes: dict[str, DrugClass] = {}
    for entry in payload["drug_classes"]:
        drug_class = DrugClass(
            id=entry["id"],
            label_en=entry["label_en"],
            label_fa=entry["label_fa"],
            aliases=tuple(entry["aliases"]),
            duplicate_allowed=bool(entry.get("duplicate_allowed", False)),
        )
        classes[drug_class.id] = drug_class

    interactions = tuple(
        InteractionRule(
            rule_id=entry["rule_id"],
            classes=frozenset(entry["classes"]),
            severity=entry["severity"],
            title_fa=entry["title_fa"],
            detail_fa=entry["detail_fa"],
        )
        for entry in payload["interactions"]
    )

    cross_reactivity = tuple(
        CrossReactivityRule(
            rule_id=entry["rule_id"],
            allergen_class=entry["allergen_class"],
            candidate_class=entry["candidate_class"],
            severity=entry["severity"],
            title_fa=entry["title_fa"],
            detail_fa=entry["detail_fa"],
        )
        for entry in payload["cross_reactivity"]
    )

    return RulesKB(
        version=payload["version"],
        source_note=payload["source_note"],
        classes=classes,
        interactions=interactions,
        cross_reactivity=cross_reactivity,
    )


# --- name normalization (English + Persian) ---

_ARABIC_YEH = "ي"  # ي
_PERSIAN_YEH = "ی"  # ی
_ARABIC_KAF = "ك"  # ك
_PERSIAN_KAF = "ک"  # ک
_ZWNJ = "‌"

_NON_WORD = re.compile(r"[^a-z0-9؀-ۿ]+")
_UNIT_TOKENS = {"mg", "mcg", "ml", "gr", "g", "iu", "tab", "tabs", "caps", "cap", "%"}


def normalize_drug_name(name: str) -> str:
    """Normalize a drug/allergen string for alias matching.

    Lowercases, unifies Arabic/Persian letter variants, drops ZWNJ and
    punctuation, and removes dose numbers and unit tokens
    (e.g. ``"Metformin 500 mg"`` → ``"metformin"``).
    """
    text = name.strip().lower()
    text = (
        text.replace(_ARABIC_YEH, _PERSIAN_YEH)
        .replace(_ARABIC_KAF, _PERSIAN_KAF)
        .replace(_ZWNJ, " ")
    )
    tokens = [token for token in _NON_WORD.split(text) if token]
    meaningful = [
        token
        for token in tokens
        if not token.isdigit() and token not in _UNIT_TOKENS
    ]
    return " ".join(meaningful)


def _matches(alias: str, normalized_name: str) -> bool:
    """Alias match: whole-token containment, or safe substring for long aliases."""
    if f" {alias} " in f" {normalized_name} ":
        return True
    return len(alias) >= 5 and alias in normalized_name


@lru_cache(maxsize=512)
def match_classes(name: str) -> frozenset[str]:
    """Return the drug-class ids an (unnormalized) name maps to."""
    normalized = normalize_drug_name(name)
    if not normalized:
        return frozenset()
    kb = load_rules_kb()
    matched: set[str] = set()
    for drug_class in kb.classes.values():
        for alias in drug_class.aliases:
            if _matches(normalize_drug_name(alias), normalized):
                matched.add(drug_class.id)
                break
    return frozenset(matched)


def class_labels(class_ids: frozenset[str] | set[str]) -> list[str]:
    kb = load_rules_kb()
    return [kb.classes[cid].label_fa for cid in sorted(class_ids)]


@dataclass(frozen=True)
class SafetyCheckResult:
    warnings: list[SafetyWarning]
    candidate_classes: frozenset[str]


def check_medication_safety(
    *,
    candidate_name: str,
    active_medication_names: list[str],
    allergen_names: list[str],
) -> SafetyCheckResult:
    """Deterministic check of one candidate against active meds + allergies.

    ``active_medication_names`` carries each active drug under every known
    name (catalog + generic) so alias matching sees both. Warning types:
    drug_interaction, allergy_conflict, duplicate_therapy. Unknown names
    never produce warnings (the engine only warns on confident class
    matches) — ``candidate_classes`` lets callers see coverage.
    """
    kb = load_rules_kb()
    candidate_classes = match_classes(candidate_name)

    # active regimen as (display name → classes); the route passes both the
    # catalog name and the generic name as separate entries
    active: list[tuple[str, frozenset[str]]] = []
    for display in active_medication_names:
        classes = match_classes(display)
        if classes:
            active.append((display, classes))
    active_class_union = frozenset().union(*[c for _, c in active]) if active else frozenset()
    allergen_classes: list[tuple[str, frozenset[str]]] = []
    for allergen in allergen_names:
        classes = match_classes(allergen)
        if classes:
            allergen_classes.append((allergen, classes))

    warnings: list[SafetyWarning] = []

    # --- drug–drug interactions (candidate × active regimen) ---
    for rule in kb.interactions:
        need = set(rule.classes)
        contributed_by_candidate = need & set(candidate_classes)
        if not contributed_by_candidate:
            continue
        remaining = need - contributed_by_candidate
        if not remaining <= set(active_class_union):
            continue
        involved = [candidate_name]
        involved.extend(
            display for display, classes in active if classes & set(remaining)
        )
        warnings.append(
            SafetyWarning(
                warning_type="drug_interaction",
                severity=rule.severity,
                title=rule.title_fa,
                detail=rule.detail_fa,
                rule_id=rule.rule_id,
                involved=involved,
            )
        )

    # --- allergy conflicts ---
    for allergen, classes in allergen_classes:
        overlap = classes & set(candidate_classes)
        if overlap:
            label = kb.classes[next(iter(overlap))].label_fa
            warnings.append(
                SafetyWarning(
                    warning_type="allergy_conflict",
                    severity="severe",
                    title=f"منع مصرف — حساسیت ثبت‌شده ({label})",
                    detail=(
                        f"بیمار به «{allergen}» حساسیت دارد و داروی کاندید در همان "
                        "کلاس دارویی قرار می‌گیرد؛ تجویز مجدد این کلاس منع مصرف دارد."
                    ),
                    rule_id=SAME_CLASS_ALLERGY_RULE_ID,
                    involved=[candidate_name, allergen],
                )
            )
            continue  # specific cross-reactivity is for non-overlapping classes
        for cross in kb.cross_reactivity:
            if cross.allergen_class in classes and cross.candidate_class in candidate_classes:
                warnings.append(
                    SafetyWarning(
                        warning_type="allergy_conflict",
                        severity=cross.severity,
                        title=cross.title_fa,
                        detail=cross.detail_fa,
                        rule_id=cross.rule_id,
                        involved=[candidate_name, allergen],
                    )
                )

    # --- duplicate therapy (same class already active) ---
    for class_id in sorted(candidate_classes):
        drug_class = kb.classes[class_id]
        if drug_class.duplicate_allowed:
            continue  # e.g. insulin: basal+bolus combinations are standard
        same_class_active = [d for d, c in active if class_id in c]
        if same_class_active:
            warnings.append(
                SafetyWarning(
                    warning_type="duplicate_therapy",
                    severity="moderate",
                    title=f"درمان تکراری — {drug_class.label_fa}",
                    detail=(
                        "بیمار هم‌اکنون دارویی از همین کلاس دریافت می‌کند "
                        f"({drug_class.label_en}); از تجویز تکراری کلاس یکسان پرهیز کنید "
                        "مگر با قصد بالینی مشخص."
                    ),
                    rule_id=DUPLICATE_THERAPY_RULE_ID,
                    involved=[candidate_name, *same_class_active],
                )
            )

    warnings.sort(key=lambda w: -SEVERITY_ORDER[w.severity])
    return SafetyCheckResult(warnings=warnings, candidate_classes=candidate_classes)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
