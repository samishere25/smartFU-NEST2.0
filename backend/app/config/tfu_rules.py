"""
Pharmacovigilance Targeted Follow-Up (TFU) Decision Agent
==========================================================

Risk-based, minimal-necessary follow-up question generation aligned with:
  - ICH E2A seriousness criteria
  - EMA GVP Module VI follow-up principles
  - Risk-based pharmacovigilance practice

Principles:
  1. Only trigger TFU when clinically or regulatorily necessary.
  2. Never exceed 5 questions (hard cap).
  3. Remove questions for data already available on the case.
  4. Prioritise: valid-case criteria → seriousness → onset → outcome → severity → concomitants.
  5. Avoid reporter fatigue — no checklist dump.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# CONFIGURATION CONSTANTS
# ────────────────────────────────────────────────────────────────
ABSOLUTE_MAX_QUESTIONS = 5          # Hard cap — never exceeded
MAX_NONSERIOUS_LISTED   = 3        # Non-serious listed event
MAX_SERIOUS_LISTED      = 5        # Serious listed event
MAX_SERIOUS_UNLISTED    = 5        # Serious unlisted / RMP risk (capped to 5)

# Values the system treats as "missing" / unfilled
MISSING_VALUES: Set[str] = {
    "", "MISSING", "UNK", "UNKNOWN", "N/A", "NA", "NONE", "NOT AVAILABLE",
}

# ICH E2A seriousness keywords (event text patterns)
SERIOUS_EVENT_KEYWORDS = [
    "death", "fatal", "life-threatening", "life threatening",
    "hospitalisation", "hospitalization", "hospital",
    "disability", "incapacity", "congenital", "birth defect",
    "medically significant", "medically important",
    "required intervention", "intervention to prevent",
]

# Special-situation keywords
SPECIAL_SITUATION_KEYWORDS = [
    "pregnancy", "pregnant", "overdose", "medication error",
    "off-label", "off label", "paediatric", "pediatric",
    "neonatal", "neonate", "elderly", "geriatric",
    "occupational exposure", "lack of efficacy",
    "misuse", "abuse", "drug interaction",
]

# RMP important-identified-risk keywords (broad, product-agnostic)
RMP_RISK_KEYWORDS = [
    "anaphylaxis", "anaphylactic", "stevens-johnson", "toxic epidermal",
    "agranulocytosis", "pancytopenia", "hepatotoxicity", "hepatic failure",
    "renal failure", "nephrotoxicity", "rhabdomyolysis",
    "cardiac arrest", "torsade", "qt prolongation",
    "suicid", "self-harm", "neuroleptic malignant",
    "serotonin syndrome", "malignant hyperthermia",
    "pulmonary embolism", "deep vein thrombosis",
]

# ────────────────────────────────────────────────────────────────
# PRODUCT + EVENT  →  MANDATORY CLINICAL QUESTIONS
# (event-specific; only added when pattern matches)
# ────────────────────────────────────────────────────────────────
_EVENT_SPECIFIC_QUESTIONS: List[Dict[str, Any]] = [
    # Bleeds
    {
        "product_pattern": "aspirin",
        "event_pattern": "bleed",
        "questions": [
            {"field_name": "anticoagulant_use",
             "question_text": "Was the patient on anticoagulants at the time of the bleeding event?",
             "criticality": "CRITICAL"},
        ],
    },
    # Anaphylaxis (any drug)
    {
        "product_pattern": "*",
        "event_pattern": "anaphylaxis",
        "questions": [
            {"field_name": "epinephrine_administered",
             "question_text": "Was epinephrine administered to treat the anaphylactic reaction?",
             "criticality": "CRITICAL"},
            {"field_name": "time_to_onset",
             "question_text": "What was the time from drug administration to onset of the anaphylactic reaction?",
             "criticality": "CRITICAL"},
        ],
    },
    # Death / fatal (any drug)
    {
        "product_pattern": "*",
        "event_pattern": "death|fatal",
        "questions": [
            {"field_name": "cause_of_death",
             "question_text": "What was the cause of death as determined by the treating physician?",
             "criticality": "CRITICAL"},
            {"field_name": "autopsy_performed",
             "question_text": "Was an autopsy performed? If yes, what were the findings?",
             "criticality": "CRITICAL"},
        ],
    },
    # Hepatotoxicity + methotrexate
    {
        "product_pattern": "methotrexate",
        "event_pattern": "hepatotoxicity|liver",
        "questions": [
            {"field_name": "liver_function_tests",
             "question_text": "Were liver function tests (ALT, AST, bilirubin) performed before and after treatment?",
             "criticality": "CRITICAL"},
        ],
    },
    # Allergy / hypersensitivity (any drug)
    {
        "product_pattern": "*",
        "event_pattern": "allergy|hypersensitivity",
        "questions": [
            {"field_name": "allergy_history",
             "question_text": "Does the patient have a known drug allergy history?",
             "criticality": "HIGH"},
        ],
    },
]

# ────────────────────────────────────────────────────────────────
# REGULATORY BASELINE QUESTION POOL (priority-ordered)
# These cover ICH valid-case criteria and causality-assessment needs.
# Only questions for MISSING data are selected.
# ────────────────────────────────────────────────────────────────
_BASELINE_QUESTION_POOL: List[Dict[str, Any]] = [
    # 1. Valid-case criteria
    {
        "field_name": "event_date",
        "case_field": "event_date",
        "question_text": "What was the date of onset of the adverse event?",
        "criticality": "CRITICAL",
        "priority": 1,
    },
    {
        "field_name": "event_outcome",
        "case_field": "event_outcome",
        "question_text": "What is the current outcome of the adverse event (resolved, ongoing, fatal, unknown)?",
        "criticality": "CRITICAL",
        "priority": 2,
    },
    # 2. Seriousness clarification
    {
        "field_name": "seriousness_criteria",
        "case_field": "is_serious",
        "question_text": "Was the event serious? If yes, which criteria applied (hospitalisation, life-threatening, disability, death, or medically significant)?",
        "criticality": "CRITICAL",
        "priority": 3,
    },
    # 3. Causality — dechallenge / rechallenge
    {
        "field_name": "dechallenge",
        "case_field": "dechallenge",
        "question_text": "Was the suspect drug stopped (dechallenge)? If so, did the event improve?",
        "criticality": "HIGH",
        "priority": 4,
    },
    # 4. Drug details
    {
        "field_name": "drug_dose",
        "case_field": "drug_dose",
        "question_text": "What was the dose and frequency of the suspect drug at the time of the event?",
        "criticality": "HIGH",
        "priority": 5,
    },
    # 5. Reporter / patient identifiability
    {
        "field_name": "patient_age",
        "case_field": "patient_age",
        "question_text": "What is the patient's age (or date of birth)?",
        "criticality": "MEDIUM",
        "priority": 6,
    },
    {
        "field_name": "patient_sex",
        "case_field": "patient_sex",
        "question_text": "What is the patient's sex?",
        "criticality": "MEDIUM",
        "priority": 7,
    },
    # 6. Concomitant medications
    {
        "field_name": "concomitant_drugs",
        "case_field": "concomitant_drugs",
        "question_text": "Was the patient taking any other medications at the time of the event?",
        "criticality": "MEDIUM",
        "priority": 8,
    },
    # 7. Reporter country (regulatory routing)
    {
        "field_name": "reporter_country",
        "case_field": "reporter_country",
        "question_text": "In which country did the adverse event occur?",
        "criticality": "MEDIUM",
        "priority": 9,
    },
    # 8. Therapy dates
    {
        "field_name": "therapy_start",
        "case_field": "therapy_start",
        "question_text": "When was the suspect drug first started?",
        "criticality": "MEDIUM",
        "priority": 10,
    },
]


# ────────────────────────────────────────────────────────────────
# HELPER UTILITIES
# ────────────────────────────────────────────────────────────────
def _is_field_filled(value: Any) -> bool:
    """Return True if the field has a meaningful (non-missing) value."""
    if value is None:
        return False
    s = str(value).strip()
    return s != "" and s.upper() not in MISSING_VALUES


def _text_matches_any(text: str, keywords: List[str]) -> bool:
    """Case-insensitive substring match against a keyword list."""
    text_lower = text.lower()
    for kw in keywords:
        if "|" in kw:
            if any(part in text_lower for part in kw.split("|")):
                return True
        elif kw in text_lower:
            return True
    return False


def _pattern_matches(pattern: str, text: str) -> bool:
    """Check if a product/event pattern matches the text (supports | and *)."""
    if pattern == "*":
        return True
    text_lower = text.lower()
    for part in pattern.lower().split("|"):
        part = part.strip()
        if part and part in text_lower:
            return True
    return False


# ────────────────────────────────────────────────────────────────
# STEP 1 — DECIDE IF TFU IS REQUIRED
# ────────────────────────────────────────────────────────────────
def _decide_tfu_required(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine whether Targeted Follow-Up is required.

    Returns:
        {
            "tfu_required": bool,
            "triggers": [str, ...],   # reasons TFU was triggered
            "is_serious": bool,
            "is_unlisted_or_rmp": bool,
            "is_special_situation": bool,
            "priority_level": "low" | "medium" | "high",
            "max_questions": int,     # cap for this case
        }
    """
    event_text = str(case_data.get("adverse_event") or "")
    outcome_text = str(case_data.get("event_outcome") or "")
    combined_text = f"{event_text} {outcome_text}"

    triggers: List[str] = []

    # ── Is serious? ─────────────────────────────────────────
    is_serious = bool(case_data.get("is_serious"))
    if not is_serious:
        is_serious = _text_matches_any(combined_text, SERIOUS_EVENT_KEYWORDS)
    if is_serious:
        triggers.append("Event is serious (ICH E2A)")

    # ── Is RMP important risk / unlisted? ───────────────────
    is_rmp = _text_matches_any(event_text, RMP_RISK_KEYWORDS)
    if is_rmp:
        triggers.append("Event matches RMP important identified risk")

    # ── Special situation? ──────────────────────────────────
    is_special = _text_matches_any(combined_text, SPECIAL_SITUATION_KEYWORDS)
    medical_history = str(case_data.get("medical_history") or "")
    if not is_special and medical_history:
        is_special = _text_matches_any(medical_history, SPECIAL_SITUATION_KEYWORDS)
    if is_special:
        triggers.append("Special situation detected (pregnancy/paediatric/overdose/etc.)")

    # ── Critical data missing? ──────────────────────────────
    critical_fields = ["event_date", "event_outcome", "is_serious"]
    missing_critical = [
        f for f in critical_fields
        if not _is_field_filled(case_data.get(f))
    ]
    if missing_critical:
        triggers.append(f"Critical data missing: {', '.join(missing_critical)}")

    tfu_required = bool(triggers)

    # ── Priority level & question cap ───────────────────────
    if is_serious and (is_rmp or is_special):
        priority = "high"
        max_q = MAX_SERIOUS_UNLISTED
    elif is_serious:
        priority = "high"
        max_q = MAX_SERIOUS_LISTED
    elif is_rmp or is_special or missing_critical:
        priority = "medium"
        max_q = MAX_NONSERIOUS_LISTED
    else:
        priority = "low"
        max_q = MAX_NONSERIOUS_LISTED

    # HARD CAP — never exceed ABSOLUTE_MAX_QUESTIONS
    max_q = min(max_q, ABSOLUTE_MAX_QUESTIONS)

    return {
        "tfu_required": tfu_required,
        "triggers": triggers,
        "is_serious": is_serious,
        "is_unlisted_or_rmp": is_rmp,
        "is_special_situation": is_special,
        "priority_level": priority,
        "max_questions": max_q,
    }


# ────────────────────────────────────────────────────────────────
# STEP 2 — COLLECT CANDIDATE QUESTIONS
# ────────────────────────────────────────────────────────────────
def _collect_candidates(
    case_data: Dict[str, Any],
    filled_fields: Set[str],
) -> List[Dict[str, Any]]:
    """
    Build prioritised candidate list:
      1. Event-specific clinical questions (product + event match)
      2. Baseline regulatory questions (only for MISSING fields)

    Already-filled data is automatically excluded.
    """
    suspect_drug = str(case_data.get("suspect_drug") or "")
    adverse_event = str(case_data.get("adverse_event") or "")

    candidates: List[Dict[str, Any]] = []
    seen_fields: Set[str] = set()

    # ── A) Event-specific questions ──────────────────────────
    for rule in _EVENT_SPECIFIC_QUESTIONS:
        if not _pattern_matches(rule["product_pattern"], suspect_drug):
            continue
        if not _pattern_matches(rule["event_pattern"], adverse_event):
            continue
        for q in rule["questions"]:
            fn = q["field_name"]
            if fn in seen_fields or fn in filled_fields:
                continue
            seen_fields.add(fn)
            candidates.append({
                "field_name": fn,
                "question_text": q["question_text"],
                "criticality": q.get("criticality", "HIGH"),
                "source": "TFU_MANDATORY",
                "priority": 0,  # event-specific always first
            })

    # ── B) Baseline regulatory questions (only if missing) ──
    for bq in _BASELINE_QUESTION_POOL:
        fn = bq["field_name"]
        case_field = bq.get("case_field", fn)
        if fn in seen_fields:
            continue
        if case_field in filled_fields:
            continue
        # Check actual case value
        if _is_field_filled(case_data.get(case_field)):
            continue
        seen_fields.add(fn)
        candidates.append({
            "field_name": fn,
            "question_text": bq["question_text"],
            "criticality": bq["criticality"],
            "source": "TFU_MANDATORY",
            "priority": bq.get("priority", 99),
        })

    # Sort by priority (0 = most important)
    candidates.sort(key=lambda c: (
        {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(c["criticality"], 9),
        c.get("priority", 99),
    ))

    return candidates


# ════════════════════════════════════════════════════════════════
# PUBLIC API — PRIMARY ENTRY POINT
# ════════════════════════════════════════════════════════════════
def tfu_decision_agent(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pharmacovigilance Targeted Follow-Up Decision Agent.

    Args:
        case_data: dict with keys from AECase:
            suspect_drug, adverse_event, event_date, event_outcome,
            is_serious, patient_age, patient_sex, drug_dose, drug_route,
            dechallenge, rechallenge, concomitant_drugs, medical_history,
            reporter_country, therapy_start, therapy_end, ...

    Returns:
        {
            "tfu_required": bool,
            "priority_level": "low" | "medium" | "high",
            "selected_questions": [question_dicts],
            "reasoning_summary": str,
            "max_questions": int,
            "triggers": [str],
        }
    """
    # Step 1: Decide if TFU is required
    decision = _decide_tfu_required(case_data)

    if not decision["tfu_required"]:
        logger.info(f"TFU Decision: NOT required for drug='{case_data.get('suspect_drug')}', "
                     f"event='{case_data.get('adverse_event')}'")
        return {
            "tfu_required": False,
            "priority_level": "low",
            "selected_questions": [],
            "reasoning_summary": "No TFU required — event is non-serious, "
                                 "not an RMP risk, no special situation, no critical data missing.",
            "max_questions": 0,
            "triggers": [],
        }

    # Step 2: Build filled-fields set from case data
    filled: Set[str] = set()
    for field_name in [
        "event_date", "event_outcome", "is_serious",
        "patient_age", "patient_sex",
        "drug_dose", "drug_route",
        "dechallenge", "rechallenge",
        "concomitant_drugs", "medical_history",
        "reporter_country", "therapy_start", "therapy_end",
        "reporter_type", "indication",
    ]:
        if _is_field_filled(case_data.get(field_name)):
            filled.add(field_name)

    # Step 3: Collect candidates (already excludes filled data)
    candidates = _collect_candidates(case_data, filled)

    # Step 4: Apply strict question cap
    max_q = decision["max_questions"]
    selected = candidates[:max_q]

    # Step 5: Build reasoning
    reasons = "; ".join(decision["triggers"])
    reasoning = (
        f"TFU required ({decision['priority_level'].upper()} priority). "
        f"Triggers: {reasons}. "
        f"Selected {len(selected)}/{len(candidates)} candidates "
        f"(cap={max_q}, filled fields excluded: {len(filled)})."
    )

    logger.info(f"TFU Decision: {reasoning}")

    return {
        "tfu_required": decision["tfu_required"],
        "priority_level": decision["priority_level"],
        "selected_questions": selected,
        "reasoning_summary": reasoning,
        "max_questions": max_q,
        "triggers": decision["triggers"],
    }


# ════════════════════════════════════════════════════════════════
# FINAL-GATE: apply to already-merged question list
# ════════════════════════════════════════════════════════════════
def apply_tfu_gate(
    merged_questions: List[Dict[str, Any]],
    case_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Final gate applied AFTER the 4-source merge (reviewer + TFU + repo + AI).

    1. Removes questions whose data is already available on the case.
    2. Prioritises by criticality + source priority.
    3. Caps to ABSOLUTE_MAX_QUESTIONS (5).

    Returns the capped, deduplicated, cleaned question list.
    """
    # Build set of filled fields
    filled: Set[str] = set()
    for field_name in [
        "event_date", "event_outcome", "is_serious",
        "patient_age", "patient_sex",
        "drug_dose", "drug_route",
        "dechallenge", "rechallenge",
        "concomitant_drugs", "medical_history",
        "reporter_country", "therapy_start", "therapy_end",
        "reporter_type", "indication",
    ]:
        if _is_field_filled(case_data.get(field_name)):
            filled.add(field_name)

    # Remove questions for already-filled data & deduplicate
    seen: Set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    for q in merged_questions:
        field = q.get("field_name") or q.get("field") or q.get("question_text", "")[:40]
        if field in seen:
            continue
        # Skip if the case already has this data
        case_field = q.get("case_field", field)
        if case_field in filled:
            logger.debug(f"TFU gate: skipping '{field}' — already filled on case")
            continue
        seen.add(field)
        cleaned.append(q)

    # Sort: REVIEWER first, then CRITICAL/HIGH, then by source priority
    SOURCE_PRIORITY = {
        "REVIEWER_QUESTION": 0,
        "TFU_MANDATORY": 1,
        "REPO_FORM": 2,
        "REPO_FORM_AI_FILTERED": 2,
        "AI_GENERATED": 3,
    }
    CRIT_PRIORITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    cleaned.sort(key=lambda q: (
        SOURCE_PRIORITY.get(q.get("source", ""), 9),
        CRIT_PRIORITY.get(q.get("criticality", "MEDIUM"), 9),
    ))

    # Apply hard cap
    capped = cleaned[:ABSOLUTE_MAX_QUESTIONS]

    if len(cleaned) > ABSOLUTE_MAX_QUESTIONS:
        logger.info(
            f"TFU gate: capped {len(cleaned)} → {len(capped)} questions "
            f"(max={ABSOLUTE_MAX_QUESTIONS}, filled={len(filled)})"
        )

    return capped


# ════════════════════════════════════════════════════════════════
# LEGACY COMPAT — match_tfu_rules() (old API, still called by
# some code paths; delegates to decision agent internally)
# ════════════════════════════════════════════════════════════════
def match_tfu_rules(
    suspect_drug: str,
    adverse_event: str,
    case_data: Optional[Dict[str, Any]] = None,
) -> list:
    """
    Match TFU rules against case drug + event.

    If full case_data is provided, uses the risk-based decision agent
    (removes already-filled fields, applies cap).
    Otherwise falls back to pattern-match only (legacy).
    """
    if not suspect_drug or not adverse_event:
        return []

    # If we have full case context, use the smart decision agent
    if case_data is not None:
        enriched = dict(case_data)
        enriched.setdefault("suspect_drug", suspect_drug)
        enriched.setdefault("adverse_event", adverse_event)
        result = tfu_decision_agent(enriched)
        return result["selected_questions"]

    # Legacy: pattern match only (no case context available)
    drug_lower = suspect_drug.lower()
    event_lower = adverse_event.lower()
    matched: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for rule in _EVENT_SPECIFIC_QUESTIONS:
        if not _pattern_matches(rule["product_pattern"], drug_lower):
            continue
        if not _pattern_matches(rule["event_pattern"], event_lower):
            continue
        for q in rule["questions"]:
            fn = q["field_name"]
            if fn not in seen:
                seen.add(fn)
                matched.append({
                    "field_name": fn,
                    "question_text": q["question_text"],
                    "source": "TFU_MANDATORY",
                    "criticality": q.get("criticality", "HIGH"),
                })

    # Always add baseline regulatory questions in legacy mode
    for bq in _BASELINE_QUESTION_POOL[:3]:  # Only top-3 in legacy
        fn = bq["field_name"]
        if fn not in seen:
            seen.add(fn)
            matched.append({
                "field_name": fn,
                "question_text": bq["question_text"],
                "source": "TFU_MANDATORY",
                "criticality": bq["criticality"],
            })

    # Legacy cap
    return matched[:ABSOLUTE_MAX_QUESTIONS]
