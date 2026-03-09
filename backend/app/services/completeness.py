"""
CIOMS Completeness Checker - Detect missing required fields from CIOMS case data.
Feeds into follow-up generation for consolidated follow-up requests.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Required CIOMS fields for a minimally complete case
REQUIRED_FIELDS = [
    "patient_initials",
    "reaction_description",
    "suspect_drug_name",
    "report_source",
]

# Extended fields that improve case quality (used for completeness scoring)
IMPORTANT_FIELDS = [
    "age",
    "sex",
    "country",
    "reaction_onset",
    "seriousness",
    "outcome",
    "dose",
    "route",
    "indication",
    "therapy_start",
    "therapy_end",
    "dechallenge",
    "rechallenge",
    "medical_history",
    "reporter_email",
    "reporter_phone",
]


def detect_missing_fields(case_data: dict) -> list:
    """
    Detect missing required CIOMS fields.

    Args:
        case_data: Dict from cioms_extractor.extract_cioms_fields()

    Returns:
        List of missing required field names.
    """
    missing = []
    for field in REQUIRED_FIELDS:
        if not case_data.get(field):
            missing.append(field)

    if missing:
        logger.info(f"CIOMS completeness: {len(missing)} required fields missing: {missing}")
    else:
        logger.info("CIOMS completeness: all required fields present")

    return missing


def detect_missing_important_fields(case_data: dict) -> list:
    """
    Detect missing important (non-required) CIOMS fields.
    These improve case quality but are not strictly required.

    Args:
        case_data: Dict from cioms_extractor.extract_cioms_fields()

    Returns:
        List of missing important field names.
    """
    missing = []
    for field in IMPORTANT_FIELDS:
        if not case_data.get(field):
            missing.append(field)
    return missing


def compute_cioms_completeness_score(case_data: dict) -> float:
    """
    Compute a completeness score (0.0 - 1.0) for a CIOMS case.

    Required fields are weighted 2x compared to important fields.

    Args:
        case_data: Dict from cioms_extractor.extract_cioms_fields()

    Returns:
        Float between 0.0 and 1.0.
    """
    total_weight = 0.0
    present_weight = 0.0

    for field in REQUIRED_FIELDS:
        total_weight += 2.0
        if case_data.get(field):
            present_weight += 2.0

    for field in IMPORTANT_FIELDS:
        total_weight += 1.0
        if case_data.get(field):
            present_weight += 1.0

    score = present_weight / total_weight if total_weight > 0 else 0.0
    logger.info(f"CIOMS completeness score: {score:.2f}")
    return round(score, 3)
