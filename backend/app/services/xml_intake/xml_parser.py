"""
XML Intake Parser — SmartFU
Supports:
  1. ICH E2B (R2/R3) format — standard PV XML used by regulators
  2. Generic flat XML — any XML with recognisable field names
"""

import re
from typing import Dict, List, Optional
from lxml import etree


# ── ICH E2B field paths (R2 tag names) ────────────────────────
_E2B_MAP = {
    "primaryid":       ".//safetyreportid",
    "patient_age":     ".//patientonsetage",
    "patient_sex":     ".//patientsex",
    "patient_initials":".//{*}patientonsetageunit/../patientnamepatient",
    "suspect_drug":    ".//medicinalproduct",
    "adverse_event":   ".//reactionmeddrapt",
    "event_date":      ".//reactionstartdate",
    "event_outcome":   ".//reactionoutcome",
    "reporter_type":   ".//primarysourcecountry",
    "reporter_country":".//{*}primarysource/reporterqualification",
    "drug_dose":       ".//structureddosagenumb",
    "drug_route":      ".//drugadministrationroute",
    "is_serious":      ".//serious",
    "reporter_email":  ".//reportertel",
}

# ── Generic XML — try common tag/attribute names ───────────────
_GENERIC_ALIASES = {
    "primaryid":        ["primaryid", "caseid", "case_id", "reportid", "id"],
    "patient_age":      ["age", "patient_age", "patientonsetage"],
    "patient_sex":      ["sex", "gender", "patient_sex", "patientsex"],
    "patient_initials": ["initials", "patient_initials", "patientname"],
    "suspect_drug":     ["drug", "suspect_drug", "medicinalproduct", "drugname", "product"],
    "adverse_event":    ["event", "adverse_event", "reaction", "reactionmeddrapt", "ae_term"],
    "event_date":       ["event_date", "onset_date", "reactionstartdate", "date"],
    "event_outcome":    ["outcome", "event_outcome", "reactionoutcome"],
    "reporter_type":    ["reporter_type", "reporter_qualification", "reporterqualification", "qualification"],
    "reporter_country": ["country", "reporter_country", "primarysourcecountry"],
    "drug_dose":        ["dose", "drug_dose", "structureddosagenumb"],
    "drug_route":       ["route", "drug_route", "drugadministrationroute"],
    "is_serious":       ["serious", "is_serious", "seriousness"],
    "reporter_email":   ["email", "reporter_email", "reportertel"],
}


def _text(el: Optional[object]) -> Optional[str]:
    if el is None:
        return None
    val = el.text if hasattr(el, "text") else None
    return val.strip() if val and val.strip() else None


def _find_e2b(root: etree._Element, xpath: str) -> Optional[str]:
    try:
        els = root.findall(xpath)
        for el in els:
            t = _text(el)
            if t:
                return t
    except Exception:
        pass
    return None


def _normalise_sex(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    v = val.strip().upper()
    if v in ("1", "M", "MALE"):
        return "M"
    if v in ("2", "F", "FEMALE"):
        return "F"
    return val[:10]


def _normalise_serious(val: Optional[str]) -> Optional[bool]:
    if not val:
        return None
    return val.strip() in ("1", "TRUE", "YES", "Y")


def _parse_e2b(root: etree._Element) -> List[Dict]:
    """Parse ICH E2B R2/R3 XML — may contain multiple <safetyreport> blocks."""
    reports = root.findall(".//safetyreport")
    if not reports:
        # Try with namespace wildcard
        reports = root.findall(".//{*}safetyreport")
    if not reports:
        reports = [root]  # single flat E2B-like doc

    cases = []
    for report in reports:
        raw: Dict = {}
        for field, xpath in _E2B_MAP.items():
            raw[field] = _find_e2b(report, xpath)

        # Fallback: grab first <medicinalproduct> if list
        if not raw.get("suspect_drug"):
            drugs = report.findall(".//medicinalproduct")
            raw["suspect_drug"] = _text(drugs[0]) if drugs else None

        # Fallback: first <reactionmeddrapt>
        if not raw.get("adverse_event"):
            rxns = report.findall(".//reactionmeddrapt")
            raw["adverse_event"] = _text(rxns[0]) if rxns else None

        case = _build_case_dict(raw)
        if case.get("suspect_drug") or case.get("adverse_event"):
            cases.append(case)

    return cases


def _parse_generic(root: etree._Element) -> List[Dict]:
    """Parse any flat XML by matching element tag names against aliases."""

    def collect_texts(node: etree._Element) -> Dict[str, str]:
        """Flatten all leaf text nodes keyed by lowercase tag (strip namespace)."""
        result = {}
        for el in node.iter():
            tag = re.sub(r"\{[^}]+\}", "", el.tag).lower()
            t = _text(el)
            if t:
                result.setdefault(tag, t)
        return result

    # Support multiple <case> / <report> / <row> / <record> elements
    case_containers = (
        root.findall(".//case") or
        root.findall(".//report") or
        root.findall(".//row") or
        root.findall(".//record") or
        root.findall(".//safetycase")
    )

    if not case_containers:
        case_containers = [root]

    cases = []
    for container in case_containers:
        flat = collect_texts(container)
        raw: Dict = {}
        for field, aliases in _GENERIC_ALIASES.items():
            for alias in aliases:
                if alias in flat:
                    raw[field] = flat[alias]
                    break

        case = _build_case_dict(raw)
        if case.get("suspect_drug") or case.get("adverse_event"):
            cases.append(case)

    return cases


def _build_case_dict(raw: Dict) -> Dict:
    """Convert raw string map → typed case dict ready for CaseService."""
    case: Dict = {}

    # primaryid — integer
    try:
        case["primaryid"] = int(str(raw.get("primaryid", "")).strip())
    except (ValueError, TypeError):
        case["primaryid"] = None  # will be auto-assigned by normaliser

    # patient_age
    try:
        case["patient_age"] = int(float(str(raw.get("patient_age", "")).strip()))
    except (ValueError, TypeError):
        case["patient_age"] = None

    case["patient_sex"]      = _normalise_sex(raw.get("patient_sex"))
    case["patient_initials"] = (raw.get("patient_initials") or "")[:20] or None
    case["suspect_drug"]     = raw.get("suspect_drug")
    case["adverse_event"]    = raw.get("adverse_event")
    case["event_date"]       = raw.get("event_date")
    case["event_outcome"]    = raw.get("event_outcome")
    case["reporter_type"]    = (raw.get("reporter_type") or "")[:10] or None
    case["reporter_country"] = (raw.get("reporter_country") or "")[:5] or None
    case["drug_dose"]        = raw.get("drug_dose")
    case["drug_route"]       = raw.get("drug_route")
    case["is_serious"]       = _normalise_serious(raw.get("is_serious"))
    case["reporter_email"]   = raw.get("reporter_email")
    case["case_status"]      = "INITIAL_RECEIVED"
    case["intake_source"]    = "XML"

    return case


# ── Public API ─────────────────────────────────────────────────

def parse_xml_bytes(file_bytes: bytes, filename: str = "") -> List[Dict]:
    """
    Parse XML file bytes into a list of case dicts.
    Auto-detects E2B vs generic format.
    Returns list of dicts compatible with CaseService.create_case().
    """
    try:
        root = etree.fromstring(file_bytes)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML file: {e}")

    tag = re.sub(r"\{[^}]+\}", "", root.tag).lower()
    is_e2b = (
        "ichicsr" in tag or
        "safetyreport" in tag or
        bool(root.findall(".//safetyreport")) or
        bool(root.findall(".//{*}safetyreport"))
    )

    if is_e2b:
        cases = _parse_e2b(root)
    else:
        cases = _parse_generic(root)

    return cases
