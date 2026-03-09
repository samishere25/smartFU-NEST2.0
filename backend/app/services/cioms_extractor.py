"""
CIOMS Form-I Extractor — Mistral LLM structured extraction with regex fallback.

Pipeline:
  PDF bytes → pdfplumber text → Mistral LLM JSON extraction → validation → 24-field dict

On LLM failure → falls back to regex-based extraction (original logic).
"""

import re
import json
import logging
from typing import Dict, Optional
from io import BytesIO
from datetime import datetime

import pdfplumber

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM extraction prompt
# ---------------------------------------------------------------------------

_CIOMS_EXTRACTION_PROMPT = """You are a pharmacovigilance data extraction system.

Extract ONLY the following CIOMS Form-I fields from the provided adverse event report text.

Return STRICTLY a valid JSON object with these exact keys:
- patient_initials (string or null) — patient's initials, e.g. "J.S."
- age (integer or null) — patient age in years
- sex (string: "M" or "F" or null)
- country (string or null) — country name or ISO code
- reaction_description (string or null) — the adverse reaction/event description
- reaction_onset (string in YYYY-MM-DD format or null) — date the reaction started
- seriousness (boolean or null) — true if the case is serious
- outcome (string or null) — outcome of the reaction (e.g. "recovered", "fatal")
- suspect_drug_name (string or null) — name of the suspect drug
- dose (string or null) — dosage information (e.g. "500mg daily")
- route (string or null) — route of administration (e.g. "oral", "IV")
- indication (string or null) — indication for use of the drug
- therapy_start (string in YYYY-MM-DD format or null)
- therapy_end (string in YYYY-MM-DD format or null)
- therapy_duration (integer or null) — duration in days
- dechallenge (string or null) — e.g. "yes", "no", "positive", "negative", "unknown"
- rechallenge (string or null) — e.g. "yes", "no", "positive", "negative", "unknown"
- concomitant_drugs (string or null) — other drugs the patient was taking
- medical_history (string or null) — relevant medical history
- report_source (string or null) — who reported: physician, pharmacist, consumer, etc.
- report_type (string or null) — initial or follow-up
- reporter_email (string or null) — email address if present
- reporter_phone (string or null) — phone number if present
- manufacturer_name (string or null) — manufacturer or marketing authorization holder

CRITICAL RULES:
1. Extract ONLY values explicitly stated in the text.
2. If a field is NOT present or unclear, set it to null. NEVER guess or infer.
3. Do NOT extract CIOMS form labels, headers, or instructions as field values.
4. If the text appears to be a blank form template with no actual patient data, return ALL fields as null.
5. Output ONLY the JSON object. No explanations, no markdown, no commentary.
"""


def extract_cioms_fields(pdf_path: str = None, file_bytes: bytes = None) -> dict:
    """
    Extract structured fields from a CIOMS Form-I PDF.

    Primary: Mistral LLM structured extraction.
    Fallback: Regex-based extraction (on LLM failure).

    Args:
        pdf_path: Path to PDF file on disk.
        file_bytes: Raw PDF bytes (used when called from upload route).

    Returns:
        dict with 24 CIOMS fields. Missing values are None.
    """
    text = _extract_text(pdf_path=pdf_path, file_bytes=file_bytes)
    if not text.strip():
        logger.warning("CIOMS extractor: empty text extracted from PDF")
        return _empty_case_data()

    # Primary: LLM extraction
    try:
        case_data = _llm_extract_cioms(text)
        if case_data is not None:
            validated = _validate_cioms_fields(case_data)
            filled = sum(1 for v in validated.values() if v is not None)
            logger.info(f"✅ CIOMS LLM extraction complete: {filled}/24 fields populated")
            return validated
    except Exception as e:
        logger.warning(f"⚠️ CIOMS LLM extraction failed: {e}")

    # Fallback: regex extraction
    logger.info("↩️ Falling back to regex-based CIOMS extraction")
    case_data = _regex_extract_cioms(text)
    validated = _validate_cioms_fields(case_data)
    filled = sum(1 for v in validated.values() if v is not None)
    logger.info(f"CIOMS regex fallback complete: {filled}/24 fields populated")
    return validated


# ---------------------------------------------------------------------------
# Text extraction (unchanged — pdfplumber)
# ---------------------------------------------------------------------------

def _extract_text(pdf_path: str = None, file_bytes: bytes = None) -> str:
    """Extract full text from PDF using pdfplumber."""
    try:
        source = pdf_path if pdf_path else BytesIO(file_bytes)
        pages = []
        with pdfplumber.open(source) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        full_text = "\n".join(pages)
        logger.info(f"CIOMS text extracted: {len(full_text)} chars from {len(pages)} pages")
        return full_text
    except Exception as e:
        logger.error(f"CIOMS PDF text extraction failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# LLM-based extraction (Mistral Cloud API)
# ---------------------------------------------------------------------------

def _llm_extract_cioms(text: str) -> Optional[dict]:
    """
    Use Mistral Cloud API to extract CIOMS fields as structured JSON.

    Returns a 24-field dict on success, or None on failure.
    """
    from app.agents.gemini_client import get_gemini_client

    client = get_gemini_client()

    # Truncate text to fit token limits (Mistral context window)
    truncated_text = text[:6000]

    user_prompt = f"REPORT TEXT:\n\n{truncated_text}"

    logger.info(f"🤖 Calling Mistral LLM for CIOMS extraction ({len(truncated_text)} chars)...")

    try:
        response = client.generate(
            system_prompt=_CIOMS_EXTRACTION_PROMPT,
            user_prompt=user_prompt,
        )
    except Exception as e:
        logger.error(f"❌ Mistral API call failed: {e}")
        return None

    if not response or not response.strip():
        logger.warning("⚠️ Mistral returned empty response")
        return None

    logger.info(f"🤖 Mistral raw response: {response[:500]}")

    # Parse JSON from response (may have surrounding text/markdown)
    parsed = _parse_llm_json(response)
    if parsed is None:
        logger.warning("⚠️ Could not parse JSON from Mistral response")
        return None

    # Map parsed response to the 24-field structure
    case_data = _empty_case_data()
    for key in case_data:
        if key in parsed and parsed[key] is not None:
            case_data[key] = parsed[key]

    return case_data


def _parse_llm_json(response_text: str) -> Optional[dict]:
    """
    Extract and parse a JSON object from LLM response text.
    Handles bare JSON, markdown code blocks, and surrounding text.
    """
    # Try direct parse first
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding any JSON object (greedy — largest match)
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Validation layer
# ---------------------------------------------------------------------------

def _validate_cioms_fields(case_data: dict) -> dict:
    """
    Validate and sanitize extracted CIOMS fields.
    Invalid values are set to None. No correction attempted.
    """
    validated = _empty_case_data()

    # --- patient_initials: short string, letters/dots only ---
    val = case_data.get("patient_initials")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 20:
            validated["patient_initials"] = val

    # --- age: integer 0-150 ---
    val = case_data.get("age")
    if val is not None:
        try:
            age_int = int(val)
            if 0 < age_int < 150:
                validated["age"] = age_int
        except (ValueError, TypeError):
            pass

    # --- sex: M or F ---
    val = case_data.get("sex")
    if isinstance(val, str):
        first = val.strip().upper()
        if first.startswith("M"):
            validated["sex"] = "M"
        elif first.startswith("F"):
            validated["sex"] = "F"

    # --- country: short text (not a paragraph) ---
    val = case_data.get("country")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 50:
            validated["country"] = val

    # --- reaction_description: non-empty text ---
    val = case_data.get("reaction_description")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 2000:
            validated["reaction_description"] = val

    # --- reaction_onset: valid date ---
    val = case_data.get("reaction_onset")
    validated["reaction_onset"] = _validate_date(val)

    # --- seriousness: boolean ---
    val = case_data.get("seriousness")
    if isinstance(val, bool):
        validated["seriousness"] = val
    elif isinstance(val, str):
        lower = val.strip().lower()
        if lower in ("yes", "true", "serious", "1"):
            validated["seriousness"] = True
        elif lower in ("no", "false", "not serious", "0"):
            validated["seriousness"] = False

    # --- outcome: short text ---
    val = case_data.get("outcome")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 200:
            validated["outcome"] = val

    # --- suspect_drug_name: non-empty text ---
    val = case_data.get("suspect_drug_name")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 500:
            validated["suspect_drug_name"] = val

    # --- dose: short text, not a narrative paragraph ---
    val = case_data.get("dose")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 200:
            validated["dose"] = val

    # --- route: short text ---
    val = case_data.get("route")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 100:
            validated["route"] = val

    # --- indication: text ---
    val = case_data.get("indication")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 500:
            validated["indication"] = val

    # --- therapy_start / therapy_end: valid dates ---
    validated["therapy_start"] = _validate_date(case_data.get("therapy_start"))
    validated["therapy_end"] = _validate_date(case_data.get("therapy_end"))

    # --- therapy_duration: integer ---
    val = case_data.get("therapy_duration")
    if val is not None:
        try:
            dur = int(val)
            if 0 <= dur <= 36500:  # max ~100 years
                validated["therapy_duration"] = dur
        except (ValueError, TypeError):
            pass

    # Compute duration from dates if not set
    if validated["therapy_duration"] is None and validated["therapy_start"] and validated["therapy_end"]:
        try:
            s = datetime.strptime(validated["therapy_start"], "%Y-%m-%d")
            e = datetime.strptime(validated["therapy_end"], "%Y-%m-%d")
            diff = (e - s).days
            if 0 <= diff <= 36500:
                validated["therapy_duration"] = diff
        except (ValueError, TypeError):
            pass

    # --- dechallenge / rechallenge: short text ---
    for field in ("dechallenge", "rechallenge"):
        val = case_data.get(field)
        if isinstance(val, str):
            val = val.strip()
            if val and len(val) <= 50:
                validated[field] = val

    # --- concomitant_drugs: text ---
    val = case_data.get("concomitant_drugs")
    if isinstance(val, str):
        val = val.strip()
        if val:
            validated["concomitant_drugs"] = val

    # --- medical_history: text ---
    val = case_data.get("medical_history")
    if isinstance(val, str):
        val = val.strip()
        if val:
            validated["medical_history"] = val

    # --- report_source: short text ---
    val = case_data.get("report_source")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 100:
            validated["report_source"] = val

    # --- report_type: short text ---
    val = case_data.get("report_type")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 50:
            validated["report_type"] = val

    # --- reporter_email: basic email check ---
    val = case_data.get("reporter_email")
    if isinstance(val, str):
        val = val.strip()
        if val and "@" in val and "." in val and len(val) <= 200:
            validated["reporter_email"] = val

    # --- reporter_phone: digits/symbols ---
    val = case_data.get("reporter_phone")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 50:
            validated["reporter_phone"] = val

    # --- manufacturer_name: text ---
    val = case_data.get("manufacturer_name")
    if isinstance(val, str):
        val = val.strip()
        if val and len(val) <= 500:
            validated["manufacturer_name"] = val

    return validated


def _validate_date(val) -> Optional[str]:
    """Validate and normalize a date value to YYYY-MM-DD, or return None."""
    if val is None:
        return None
    if not isinstance(val, str):
        return None
    val = val.strip()
    if not val:
        return None

    # Try common date formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y%m%d",
                "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(val.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


# ---------------------------------------------------------------------------
# Regex-based extraction (fallback — original logic preserved)
# ---------------------------------------------------------------------------

def _first_match(text: str, patterns: list) -> Optional[str]:
    """Return the first regex match group(1) from a list of patterns, or None."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            value = m.group(1).strip()
            if value:
                return value
    return None


def _parse_date_regex(text: str, patterns: list) -> Optional[str]:
    """Try to extract and normalize a date string (YYYY-MM-DD) from patterns."""
    raw = _first_match(text, patterns)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y%m%d",
                "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _regex_extract_cioms(text: str) -> dict:
    """Parse all 24 CIOMS fields from extracted text using regex (fallback)."""

    case_data = _empty_case_data()

    # --- Patient Information ---
    case_data["patient_initials"] = _first_match(text, [
        r"patient\s+initials?\s*[:\-]?\s*([A-Z]{1,4}(?:\.\s*[A-Z]\.?)*)",
        r"initials?\s*[:\-]?\s*([A-Z]{1,4})",
    ])

    age_raw = _first_match(text, [
        r"(?:patient\s+)?age\s*[:\-]?\s*(\d{1,3})\s*(?:years?|yrs?|yr)?",
        r"(\d{1,3})\s*(?:years?\s+old|yr\s+old)",
    ])
    if age_raw:
        try:
            age_val = int(age_raw)
            if 0 < age_val < 150:
                case_data["age"] = age_val
        except ValueError:
            pass

    sex_raw = _first_match(text, [
        r"(?:patient\s+)?(?:sex|gender)\s*[:\-]?\s*(male|female|M|F)\b",
        r"\b(male|female)\b",
    ])
    if sex_raw:
        case_data["sex"] = sex_raw[0].upper()

    case_data["country"] = _first_match(text, [
        r"country\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    # --- Reaction / Event ---
    case_data["reaction_description"] = _first_match(text, [
        r"(?:adverse\s+)?(?:reaction|event)\s*(?:description|term)?\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"describe\s+(?:the\s+)?(?:adverse\s+)?(?:reaction|event)\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["reaction_onset"] = _parse_date_regex(text, [
        r"(?:date\s+of\s+)?(?:onset|reaction\s+onset)\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"onset\s+date\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    seriousness_raw = _first_match(text, [
        r"seriousness?\s*[:\-]?\s*(yes|no|serious|not\s+serious)",
        r"(?:is\s+)?serious\s*[:\-]?\s*(yes|no)",
    ])
    if seriousness_raw:
        case_data["seriousness"] = seriousness_raw.strip().lower() in ("yes", "serious")

    case_data["outcome"] = _first_match(text, [
        r"outcome\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"result\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    # --- Suspect Drug ---
    case_data["suspect_drug_name"] = _first_match(text, [
        r"(?:suspect(?:ed)?\s+)?drug(?:\s+name)?\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"medication\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"product(?:\s+name)?\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["dose"] = _first_match(text, [
        r"(?:daily\s+)?dos(?:e|age)\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["route"] = _first_match(text, [
        r"route(?:\s+of\s+administration)?\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"administration\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["indication"] = _first_match(text, [
        r"indication\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"indication\s+for\s+use\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    # --- Therapy Dates ---
    case_data["therapy_start"] = _parse_date_regex(text, [
        r"therapy\s+start(?:\s+date)?\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"start(?:\s+date)?\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["therapy_end"] = _parse_date_regex(text, [
        r"therapy\s+end(?:\s+date)?\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"(?:stop|end)(?:\s+date)?\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    if case_data["therapy_start"] and case_data["therapy_end"]:
        try:
            start_dt = datetime.strptime(case_data["therapy_start"], "%Y-%m-%d")
            end_dt = datetime.strptime(case_data["therapy_end"], "%Y-%m-%d")
            case_data["therapy_duration"] = (end_dt - start_dt).days
        except ValueError:
            pass
    else:
        dur_raw = _first_match(text, [
            r"(?:therapy\s+)?duration\s*[:\-]?\s*(\d+)\s*(?:days?|d)\b",
        ])
        if dur_raw:
            try:
                case_data["therapy_duration"] = int(dur_raw)
            except ValueError:
                pass

    # --- Dechallenge / Rechallenge ---
    dech_raw = _first_match(text, [
        r"dechallenge\s*[:\-]?\s*(yes|no|positive|negative|unknown|N/?A)",
    ])
    if dech_raw:
        case_data["dechallenge"] = dech_raw.strip()

    rech_raw = _first_match(text, [
        r"rechallenge\s*[:\-]?\s*(yes|no|positive|negative|unknown|N/?A)",
    ])
    if rech_raw:
        case_data["rechallenge"] = rech_raw.strip()

    # --- Additional Clinical ---
    case_data["concomitant_drugs"] = _first_match(text, [
        r"concomitant\s+(?:drugs?|medications?)\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["medical_history"] = _first_match(text, [
        r"(?:relevant\s+)?medical\s+history\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"(?:relevant\s+)?(?:past\s+)?history\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    # --- Reporter ---
    case_data["report_source"] = _first_match(text, [
        r"report(?:er)?\s+(?:source|type|qualification)\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"reported\s+by\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"qualifier\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["report_type"] = _first_match(text, [
        r"report\s+type\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"type\s+of\s+report\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    case_data["reporter_email"] = _first_match(text, [
        r"e?-?mail\s*[:\-]?\s*([\w.+-]+@[\w-]+\.[\w.]+)",
        r"([\w.+-]+@[\w-]+\.[\w.]+)",
    ])

    case_data["reporter_phone"] = _first_match(text, [
        r"(?:phone|tel(?:ephone)?|fax)\s*[:\-]?\s*([+\d\s\-().]{7,20})",
    ])

    case_data["manufacturer_name"] = _first_match(text, [
        r"manufacturer(?:\s+name)?\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"(?:marketing\s+)?authorization\s+holder\s*[:\-]?\s*(.+?)(?:\n|$)",
    ])

    filled = sum(1 for v in case_data.values() if v is not None)
    logger.info(f"CIOMS regex extraction: {filled}/24 fields populated")

    return case_data


# ---------------------------------------------------------------------------
# Empty template
# ---------------------------------------------------------------------------

def _empty_case_data() -> dict:
    """Return the 24-field CIOMS case_data dict with all values set to None."""
    return {
        "patient_initials": None,
        "age": None,
        "sex": None,
        "country": None,
        "reaction_description": None,
        "reaction_onset": None,
        "seriousness": None,
        "outcome": None,
        "suspect_drug_name": None,
        "dose": None,
        "route": None,
        "indication": None,
        "therapy_start": None,
        "therapy_end": None,
        "therapy_duration": None,
        "dechallenge": None,
        "rechallenge": None,
        "concomitant_drugs": None,
        "medical_history": None,
        "report_source": None,
        "report_type": None,
        "reporter_email": None,
        "reporter_phone": None,
        "manufacturer_name": None,
    }
