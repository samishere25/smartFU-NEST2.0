"""
Feature Adapter - Maps CIOMS 24-field case_data to the feature structure
consumed by the existing ML models.

This adapter bridges CIOMS extraction output to the existing
ResponsePredictionService.prepare_features() input format.
It does NOT replace prepare_features() — it produces the case_data dict
that prepare_features() already expects.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def build_model_features(case_data: dict) -> dict:
    """
    Map CIOMS case_data (24 fields) to the case_data dict format
    that ResponsePredictionService.prepare_features() consumes.

    The existing ML pipeline expects keys like:
        patient_age, sex, suspect_drug, adverse_event, event_date,
        reporter_type, dose, route, country, risk_score, ...

    This function translates CIOMS field names to those expected keys.

    Args:
        case_data: Dict from cioms_extractor.extract_cioms_fields()

    Returns:
        Dict compatible with ResponsePredictionService.prepare_features()
    """
    # Compute therapy_duration from dates if not already set
    therapy_duration = case_data.get("therapy_duration")
    if therapy_duration is None:
        start = case_data.get("therapy_start")
        end = case_data.get("therapy_end")
        if start and end:
            try:
                start_dt = datetime.strptime(str(start), "%Y-%m-%d")
                end_dt = datetime.strptime(str(end), "%Y-%m-%d")
                therapy_duration = (end_dt - start_dt).days
            except (ValueError, TypeError):
                therapy_duration = None

    # Map CIOMS field names → existing ML pipeline field names
    mapped = {
        "patient_age": case_data.get("age"),
        "sex": _normalize_sex(case_data.get("sex")),
        "suspect_drug": case_data.get("suspect_drug_name"),
        "adverse_event": case_data.get("reaction_description"),
        "event_date": case_data.get("reaction_onset"),
        "reporter_type": _normalize_reporter_type(case_data.get("report_source")),
        "dose": case_data.get("dose"),
        "route": case_data.get("route"),
        "country": case_data.get("country"),
        "is_serious": case_data.get("seriousness"),
        "event_outcome": case_data.get("outcome"),
        "therapy_duration": therapy_duration,
    }

    filled = sum(1 for v in mapped.values() if v is not None)
    logger.info(f"Feature adapter: mapped {filled}/12 fields from CIOMS to ML input")

    return mapped


def _normalize_sex(raw: Optional[str]) -> Optional[str]:
    """Normalize sex value to M/F."""
    if not raw:
        return None
    upper = str(raw).upper().strip()
    if upper in ("M", "MALE"):
        return "M"
    if upper in ("F", "FEMALE"):
        return "F"
    return upper[:1] if upper else None


def _normalize_reporter_type(raw: Optional[str]) -> Optional[str]:
    """Normalize reporter type to FAERS codes (MD, HP, CN, etc.)."""
    if not raw:
        return None
    lower = str(raw).lower().strip()
    reporter_map = {
        "physician": "MD", "doctor": "MD", "md": "MD",
        "pharmacist": "PH", "rph": "PH", "ph": "PH",
        "nurse": "HP", "rn": "HP", "health professional": "HP", "hp": "HP",
        "consumer": "CN", "patient": "CN", "cn": "CN",
        "lawyer": "LW", "attorney": "LW", "lw": "LW",
        "other": "OT",
    }
    return reporter_map.get(lower, str(raw).strip()[:10].upper())
