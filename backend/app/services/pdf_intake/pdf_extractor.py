"""
PDF Extractor - Parse, detect template, extract fields (rules + LLM fallback).
Handles CIOMS, STRUCTURED, and GENERIC pharmacovigilance PDFs.
"""

import re
import json
import logging
from typing import Dict, Tuple, Literal

import pdfplumber
import httpx
from io import BytesIO

logger = logging.getLogger(__name__)

# Ollama config
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"
OLLAMA_TIMEOUT = 10  # seconds - critical for 8GB M1


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract full text from PDF using pdfplumber.
    Returns empty string on failure (never crashes).
    """
    try:
        text_pages = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)

        full_text = "\n".join(text_pages)
        logger.info(f"📄 PDF extracted: {len(full_text)} chars from {len(text_pages)} pages")
        return full_text

    except Exception as e:
        logger.error(f"❌ PDF parsing failed: {e}")
        return ""


def detect_template(text: str) -> Literal["CIOMS", "STRUCTURED", "GENERIC"]:
    """
    Detect PDF template type based on content keywords.

    CIOMS: ≥2 CIOMS-specific keywords found.
    STRUCTURED: contains labeled fields like "Age:", "Drug:".
    GENERIC: fallback for free-text reports.
    """
    upper_text = text.upper()

    # CIOMS detection
    cioms_keywords = [
        "CIOMS",
        "PATIENT INFORMATION",
        "SUSPECT DRUG",
        "ADVERSE REACTION",
        "REPORTER",
    ]
    cioms_matches = sum(1 for kw in cioms_keywords if kw in upper_text)
    if cioms_matches >= 2:
        logger.info(f"🔍 Template: CIOMS (matched {cioms_matches} keywords)")
        return "CIOMS"

    # STRUCTURED detection
    structured_labels = [
        r"(?:patient\s+)?age\s*:",
        r"(?:suspect\s+)?drug\s*:",
        r"(?:adverse\s+)?event\s*:",
        r"date\s*:",
        r"sex\s*:",
        r"dose\s*:",
        r"route\s*:",
        r"outcome\s*:",
    ]
    struct_matches = sum(
        1 for pat in structured_labels if re.search(pat, text, re.IGNORECASE)
    )
    if struct_matches >= 3:
        logger.info(f"🔍 Template: STRUCTURED (matched {struct_matches} labels)")
        return "STRUCTURED"

    logger.info("🔍 Template: GENERIC (no structured pattern detected)")
    return "GENERIC"


def rule_extract_fields(text: str) -> Tuple[Dict, float]:
    """
    Rule-based regex extraction of pharmacovigilance fields.
    Returns (extracted_fields_dict, confidence_score).
    Confidence = non_null_fields / total_expected_fields.
    """
    fields = {}

    # Define extraction patterns (case-insensitive, multiline)
    patterns = {
        "patient_age": [
            r"(?:patient\s+)?age[\s:]+(\d{1,3})\s*(?:years?|yrs?|yr)?",
            r"(\d{1,3})\s*(?:years?\s+old|year\s+old|yrs?\s+old)",
            r"age[\s:]*(\d{1,3})",
        ],
        "patient_sex": [
            r"(?:patient\s+)?(?:sex|gender)[\s:]+(\w+)",
            r"\b(male|female|M|F)\b",
        ],
        "suspect_drug": [
            r"(?:suspect(?:ed)?\s+)?drug(?:\s+name)?[\s:]+(.+?)(?:\n|$)",
            r"medication[\s:]+(.+?)(?:\n|$)",
            r"product(?:\s+name)?[\s:]+(.+?)(?:\n|$)",
        ],
        "adverse_event": [
            r"(?:adverse\s+)?(?:event|reaction)(?:\s+description)?[\s:]+(.+?)(?:\n|$)",
            r"(?:adverse\s+)?reaction[\s:]+(.+?)(?:\n|$)",
            r"event\s+(?:description|term)[\s:]+(.+?)(?:\n|$)",
        ],
        "event_date": [
            r"(?:event\s+)?date(?:\s+of\s+(?:onset|event))?[\s:]+(.+?)(?:\n|$)",
            r"(?:date\s+of\s+)?onset[\s:]+(.+?)(?:\n|$)",
        ],
        "event_outcome": [
            r"outcome[\s:]+(.+?)(?:\n|$)",
            r"result[\s:]+(.+?)(?:\n|$)",
        ],
        "reporter_type": [
            r"reporter(?:\s+type|\s+qualification)?[\s:]+(.+?)(?:\n|$)",
            r"(?:reported\s+by|qualifier)[\s:]+(.+?)(?:\n|$)",
        ],
        "is_serious": [
            r"(?:serious(?:ness)?|is\s+serious)[\s:]+(\w+)",
            r"serious[\s:]*(?:\[?[xX✓✔]\]?\s*)?(yes|no)",
        ],
        "drug_dose": [
            r"(?:daily\s+)?dos(?:e|age)[\s:]+(.+?)(?:\n|$)",
        ],
        "drug_route": [
            r"(?:route(?:\s+of\s+administration)?)[\s:]+(.+?)(?:\n|$)",
            r"administration[\s:]+(.+?)(?:\n|$)",
        ],
        "reporter_country": [
            r"country[\s:]+(.+?)(?:\n|$)",
        ],
    }

    total_fields = len(patterns)

    for field_name, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                if value:
                    fields[field_name] = value
                    break

    non_null = sum(1 for v in fields.values() if v is not None)
    confidence = non_null / total_fields if total_fields > 0 else 0.0

    logger.info(f"📋 Rule extraction: {non_null}/{total_fields} fields found (confidence: {confidence:.2f})")
    for k, v in fields.items():
        logger.info(f"   {k}: {v}")

    return fields, confidence


def llm_extract_fields(text: str) -> Dict:
    """
    Ollama (mistral) LLM fallback extraction.
    Only called when template == GENERIC and rule_confidence < 0.5.

    Safeguards:
    - 10s hard timeout (critical for 8GB M1)
    - Graceful fallback on ANY failure
    - Strict JSON-only prompt
    """
    prompt = f"""Extract pharmacovigilance fields from this adverse event report.
Return STRICTLY valid JSON with these exact keys:
- patient_age (integer or null)
- patient_sex (string: "M" or "F" or null)
- suspect_drug (string or null)
- adverse_event (string or null)
- event_date (string in YYYY-MM-DD format or null)
- event_outcome (string or null)
- reporter_type (string or null)
- is_serious (boolean or null)
- drug_dose (string or null)
- drug_route (string or null)
- reporter_country (string or null)

RULES:
- If a field is NOT explicitly stated in the text, return null.
- Do NOT infer or guess missing data.
- Do NOT add explanation or commentary.
- Output ONLY the JSON object, nothing else.

TEXT:
{text[:3000]}"""

    try:
        logger.info(f"🤖 Calling Ollama ({OLLAMA_MODEL}) with {OLLAMA_TIMEOUT}s timeout...")

        response = httpx.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 512,
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()

        result_text = response.json().get("response", "")
        logger.info(f"🤖 Ollama raw response: {result_text[:500]}")

        # Extract JSON from response (may have surrounding text)
        json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
        if not json_match:
            logger.warning("⚠️ No JSON object found in Ollama response")
            return {}

        parsed = json.loads(json_match.group())
        logger.info(f"✅ Ollama extracted {sum(1 for v in parsed.values() if v is not None)} fields")
        return parsed

    except httpx.TimeoutException:
        logger.warning("⏰ Ollama timeout (10s) - falling back to rule extraction")
        return {}
    except httpx.ConnectError:
        logger.warning("🔌 Ollama not running (connection refused) - falling back to rule extraction")
        return {}
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ Ollama JSON parse failed: {e} - falling back to rule extraction")
        return {}
    except Exception as e:
        logger.error(f"❌ Ollama error: {e} - falling back to rule extraction")
        return {}


def extract_from_pdf(file_bytes: bytes) -> Dict:
    """
    Main orchestrator: PDF → text → template detect → extract → normalize.

    Returns dict with:
    - fields: extracted field values
    - metadata: template type, confidence, whether LLM was used
    """
    # Step 1: Extract text
    text = extract_pdf_text(file_bytes)
    if not text.strip():
        logger.error("❌ Empty PDF text - cannot extract fields")
        return {
            "fields": {},
            "metadata": {
                "template": "UNKNOWN",
                "rule_confidence": 0.0,
                "llm_used": False,
                "error": "PDF text extraction failed or PDF is empty",
            },
        }

    # Step 2: Detect template
    template = detect_template(text)

    # Step 3: Rule-based extraction
    rule_fields, rule_confidence = rule_extract_fields(text)

    # Step 4: LLM fallback (only for GENERIC + low confidence)
    llm_used = False
    llm_fields = {}

    if template == "GENERIC" and rule_confidence < 0.5:
        logger.info("🤖 Triggering LLM fallback (GENERIC template + low rule confidence)")
        llm_fields = llm_extract_fields(text)
        llm_used = bool(llm_fields)

        # Merge: LLM fills gaps in rule extraction (rule fields take priority)
        if llm_fields:
            for key, value in llm_fields.items():
                if key not in rule_fields or rule_fields[key] is None:
                    if value is not None:
                        rule_fields[key] = value
                        logger.info(f"   🤖→ LLM filled: {key} = {value}")

    final_fields = rule_fields
    final_confidence = sum(1 for v in final_fields.values() if v is not None) / 11  # 11 total fields

    logger.info(f"📊 Extraction complete: template={template}, confidence={final_confidence:.2f}, llm_used={llm_used}")

    return {
        "fields": final_fields,
        "metadata": {
            "template": template,
            "rule_confidence": rule_confidence,
            "final_confidence": final_confidence,
            "llm_used": llm_used,
            "text_length": len(text),
        },
    }
