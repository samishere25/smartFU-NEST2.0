"""
Regulatory Seriousness Evaluator — Deterministic, rule-based.

ICH E2B / CIOMS criteria for serious adverse events.
Independent of ML risk score.

A case is SERIOUS if ANY of these are true:
- Death
- Life-threatening
- Hospitalization (initial or prolonged)
- Disability / incapacity
- Congenital anomaly / birth defect
- Medically important condition

This function does NOT use seriousness_score (ML risk).
ML risk controls prioritization only.
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ICH E2B seriousness criteria keywords
_DEATH_KEYWORDS = [
    "death", "died", "fatal", "deceased", "mortality",
]
_LIFE_THREATENING_KEYWORDS = [
    "life-threatening", "life threatening", "near-fatal",
]
_HOSPITALIZATION_KEYWORDS = [
    "hospitalization", "hospitalisation", "hospitalized", "hospitalised",
    "hospital admission", "admitted to hospital", "inpatient",
    "prolonged hospitalization", "prolonged hospitalisation",
]
_DISABILITY_KEYWORDS = [
    "disability", "incapacity", "persistent disability",
    "significant disability", "unable to work",
]
_CONGENITAL_KEYWORDS = [
    "congenital anomaly", "congenital abnormality", "birth defect",
    "congenital malformation",
]
_MEDICALLY_IMPORTANT_KEYWORDS = [
    "medically important", "medically significant",
    "required intervention", "required medical intervention",
    "anaphylaxis", "seizure", "liver failure", "renal failure",
    "stevens-johnson", "toxic epidermal", "agranulocytosis",
    "aplastic anemia", "aplastic anaemia",
]


def evaluate_regulatory_seriousness(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate regulatory seriousness using ICH E2B criteria.

    Args:
        case_data: Dict with case fields. Accepts:
            - event_outcome: str (e.g. "DE" for death, "HO" for hospitalization)
            - adverse_event: str (free text reaction description)
            - is_serious: bool (from source form, if explicitly marked)
            - seriousness: any truthy value from CIOMS extraction
            - Any additional text fields that may contain seriousness signals

    Returns:
        {
            "is_serious": bool,
            "seriousness_criteria": ["death", "hospitalization", ...],
            "seriousness_source": "regulatory_rule",
            "detail": str,
        }
    """
    criteria_met = []

    # ── 1. Check explicit seriousness flag from source ──
    if case_data.get("is_serious") is True or case_data.get("seriousness") is True:
        criteria_met.append("source_flagged_serious")

    # ── 2. Check event_outcome code (FAERS standard codes) ──
    outcome = str(case_data.get("event_outcome") or "").strip().upper()
    if outcome in ("DE", "DEATH"):
        criteria_met.append("death")
    elif outcome in ("LT", "LIFE-THREATENING"):
        criteria_met.append("life_threatening")
    elif outcome in ("HO", "HOSPITALIZATION", "HOSPITALIZED"):
        criteria_met.append("hospitalization")
    elif outcome in ("DS", "DISABILITY"):
        criteria_met.append("disability")
    elif outcome in ("CA", "CONGENITAL"):
        criteria_met.append("congenital_anomaly")
    elif outcome in ("RI", "REQUIRED INTERVENTION", "OT"):
        # OT (Other) can be medically important — check text below
        pass

    # ── 3. Text-based detection from adverse_event + medical_history ──
    text_fields = [
        str(case_data.get("adverse_event") or ""),
        str(case_data.get("reaction_description") or ""),
        str(case_data.get("medical_history") or ""),
        str(case_data.get("event_outcome") or ""),
    ]
    combined_text = " ".join(text_fields).lower()

    if _any_match(combined_text, _DEATH_KEYWORDS) and "death" not in criteria_met:
        criteria_met.append("death")
    if _any_match(combined_text, _LIFE_THREATENING_KEYWORDS) and "life_threatening" not in criteria_met:
        criteria_met.append("life_threatening")
    if _any_match(combined_text, _HOSPITALIZATION_KEYWORDS) and "hospitalization" not in criteria_met:
        criteria_met.append("hospitalization")
    if _any_match(combined_text, _DISABILITY_KEYWORDS) and "disability" not in criteria_met:
        criteria_met.append("disability")
    if _any_match(combined_text, _CONGENITAL_KEYWORDS) and "congenital_anomaly" not in criteria_met:
        criteria_met.append("congenital_anomaly")
    if _any_match(combined_text, _MEDICALLY_IMPORTANT_KEYWORDS) and "medically_important" not in criteria_met:
        criteria_met.append("medically_important")

    is_serious = len(criteria_met) > 0

    detail = (
        f"Serious: {', '.join(criteria_met)}" if is_serious
        else "No ICH E2B seriousness criteria met"
    )

    logger.info(f"Regulatory seriousness: is_serious={is_serious}, criteria={criteria_met}")

    return {
        "is_serious": is_serious,
        "seriousness_criteria": criteria_met,
        "seriousness_source": "regulatory_rule",
        "detail": detail,
    }


def get_seriousness_level(seriousness_result: Dict[str, Any]) -> str:
    """
    Convert seriousness evaluation to lifecycle-compatible level string.

    Used for lifecycle deadline determination (7-day vs 15-day).

    Returns: "critical", "high", "medium", or "low"
    """
    criteria = seriousness_result.get("seriousness_criteria", [])

    if "death" in criteria:
        return "critical"
    if "life_threatening" in criteria:
        return "critical"
    if "hospitalization" in criteria or "congenital_anomaly" in criteria:
        return "high"
    if "disability" in criteria or "medically_important" in criteria:
        return "high"
    if "source_flagged_serious" in criteria:
        return "medium"
    return "low"


def _any_match(text: str, keywords: list) -> bool:
    """Check if any keyword appears in text (word boundary aware)."""
    for kw in keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            return True
    return False
