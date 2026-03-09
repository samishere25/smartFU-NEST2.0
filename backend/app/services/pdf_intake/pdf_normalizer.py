"""
PDF Normalizer - Map extracted fields to AECase schema, validate, generate primaryid.
Does NOT modify AECase model or database schema.
"""

import re
import time
import logging
from typing import Dict, Tuple, List, Optional
from datetime import datetime

from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def generate_primaryid() -> int:
    """
    Generate a unique primaryid for PDF-uploaded cases.
    Uses 900M+ range to avoid collision with FAERS IDs (180M-190M range).
    """
    pid = 900_000_000 + int(time.time() * 1000) % 100_000_000
    logger.info(f"🔑 Generated primaryid: {pid}")
    return pid


def normalize_to_aecase(extracted: Dict) -> Dict:
    """
    Map extracted PDF fields to AECase column names with correct types.

    CRITICAL: AECase has these NOT NULL fields:
    - suspect_drug (String 500)
    - adverse_event (String 1000)
    - primaryid (Integer) — handled separately in route

    All other fields are nullable.
    """
    fields = extracted.get("fields", {})
    normalized = {}

    # suspect_drug — NOT NULL, must have a value
    suspect_drug = fields.get("suspect_drug")
    if suspect_drug and str(suspect_drug).strip():
        normalized["suspect_drug"] = str(suspect_drug).strip()[:500]
    else:
        normalized["suspect_drug"] = "UNKNOWN DRUG"
        logger.warning("⚠️ suspect_drug missing — set to 'UNKNOWN DRUG'")

    # adverse_event — NOT NULL, must have a value
    # PDF may have "adverse_event" or "reaction" key
    adverse_event = fields.get("adverse_event") or fields.get("reaction")
    if adverse_event and str(adverse_event).strip():
        normalized["adverse_event"] = str(adverse_event).strip()[:1000]
    else:
        normalized["adverse_event"] = "UNKNOWN EVENT"
        logger.warning("⚠️ adverse_event missing — set to 'UNKNOWN EVENT'")

    # patient_age — Integer, nullable
    age_raw = fields.get("patient_age")
    if age_raw is not None:
        try:
            age_val = int(re.findall(r'\d+', str(age_raw))[0])
            if 0 < age_val < 150:
                normalized["patient_age"] = age_val
        except (ValueError, IndexError):
            logger.warning(f"⚠️ Could not parse patient_age: {age_raw}")

    # patient_sex — String(10), normalize to M/F
    sex_raw = fields.get("patient_sex")
    if sex_raw:
        lower_sex = str(sex_raw).lower().strip()
        if lower_sex in ("m", "male", "man", "boy"):
            normalized["patient_sex"] = "M"
        elif lower_sex in ("f", "female", "woman", "girl"):
            normalized["patient_sex"] = "F"
        else:
            normalized["patient_sex"] = str(sex_raw).strip()[:10]

    # event_date — DateTime, nullable
    date_raw = fields.get("event_date")
    if date_raw:
        try:
            parsed_date = date_parser.parse(str(date_raw), fuzzy=True)
            normalized["event_date"] = parsed_date
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Could not parse event_date: {date_raw}")

    # event_outcome — String(100), nullable
    outcome_raw = fields.get("event_outcome")
    if outcome_raw and str(outcome_raw).strip():
        normalized["event_outcome"] = str(outcome_raw).strip().upper()[:100]

    # reporter_type — String(10), nullable
    reporter_raw = fields.get("reporter_type")
    if reporter_raw and str(reporter_raw).strip():
        # Normalize common reporter types to FAERS codes
        reporter_map = {
            "physician": "MD", "doctor": "MD", "md": "MD",
            "pharmacist": "RPH", "rph": "RPH",
            "nurse": "RN", "rn": "RN",
            "consumer": "CN", "patient": "CN",
            "lawyer": "LW", "attorney": "LW",
            "other": "OT",
        }
        lower_reporter = str(reporter_raw).lower().strip()
        normalized["reporter_type"] = reporter_map.get(lower_reporter, str(reporter_raw).strip()[:10])

    # is_serious — Boolean, default False
    serious_raw = fields.get("is_serious")
    if serious_raw is not None:
        if isinstance(serious_raw, bool):
            normalized["is_serious"] = serious_raw
        else:
            lower_val = str(serious_raw).lower().strip()
            normalized["is_serious"] = lower_val in ("yes", "true", "1", "y")

    # drug_dose — String(500), nullable
    dose_raw = fields.get("drug_dose")
    if dose_raw and str(dose_raw).strip():
        normalized["drug_dose"] = str(dose_raw).strip()[:500]

    # drug_route — String(100), nullable
    route_raw = fields.get("drug_route")
    if route_raw and str(route_raw).strip():
        normalized["drug_route"] = str(route_raw).strip()[:100]

    # reporter_country — String(5), normalize to ISO code
    country_raw = fields.get("reporter_country")
    if country_raw and str(country_raw).strip():
        country_map = {
            "india": "IN", "united states": "US", "america": "US", "usa": "US",
            "uk": "GB", "united kingdom": "GB", "england": "GB",
            "canada": "CA", "germany": "DE", "france": "FR", "japan": "JP",
            "china": "CN", "australia": "AU", "brazil": "BR", "italy": "IT",
            "spain": "ES", "mexico": "MX", "russia": "RU", "south korea": "KR",
        }
        lower_country = str(country_raw).lower().strip()
        normalized["reporter_country"] = country_map.get(lower_country, str(country_raw).strip()[:5].upper())

    # Always set initial status
    normalized["case_status"] = "INITIAL_RECEIVED"

    logger.info(f"✅ Normalized {len(normalized)} fields for AECase insertion")
    for k, v in normalized.items():
        logger.info(f"   {k}: {v}")

    return normalized


def validate_pv_case(normalized: Dict) -> Tuple[bool, List[str]]:
    """
    Validate minimum ICH pharmacovigilance case criteria:
    1. Identifiable patient (age or sex)
    2. Identifiable reporter (reporter_type)
    3. Suspect drug
    4. Adverse event

    Returns (is_complete, list_of_missing_criteria).
    Does NOT block insertion — just marks completeness.
    """
    missing = []

    # Check identifiable patient
    has_patient = (
        normalized.get("patient_age") is not None
        or normalized.get("patient_sex") is not None
    )
    if not has_patient:
        missing.append("identifiable_patient (no age or sex)")

    # Check identifiable reporter
    has_reporter = normalized.get("reporter_type") is not None
    if not has_reporter:
        missing.append("identifiable_reporter (no reporter type)")

    # Check suspect drug (real value, not placeholder)
    drug = normalized.get("suspect_drug", "")
    if not drug or drug == "UNKNOWN DRUG":
        missing.append("suspect_drug (missing or unknown)")

    # Check adverse event (real value, not placeholder)
    event = normalized.get("adverse_event", "")
    if not event or event == "UNKNOWN EVENT":
        missing.append("adverse_event (missing or unknown)")

    is_complete = len(missing) == 0

    if is_complete:
        logger.info("✅ PV case meets all 4 ICH minimum criteria")
    else:
        logger.warning(f"⚠️ PV case missing {len(missing)} criteria: {missing}")

    return is_complete, missing
