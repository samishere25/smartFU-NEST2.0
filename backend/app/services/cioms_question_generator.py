"""
CIOMS Question Generator - Mistral AI-based follow-up question generation.

Uses the same Mistral API client (GeminiClient) as the existing graph.py agents
to dynamically generate context-aware follow-up questions for missing CIOMS fields.

NO static templates — all questions are AI-generated based on missing fields + case context.
"""

import re
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_cioms_questions(
    missing_fields: List[str],
    case_context: Optional[Dict] = None,
    language: str = "en",
) -> Dict[str, str]:
    """
    Generate follow-up questions for missing CIOMS fields using Mistral AI.

    Uses the same GeminiClient (Mistral) that the existing agents use.

    Args:
        missing_fields: List of missing CIOMS field names.
        case_context: Optional dict with known case data for context
                      (e.g., suspect_drug_name, reaction_description, age).
        language: Language code for generated questions (en, hi, es, fr, de, ja, zh, pt, ar)

    Returns:
        Dict mapping field_name → AI-generated question_text.
    """
    if not missing_fields:
        return {}

    prompt = _build_prompt(missing_fields, case_context, language)
    result = _call_mistral(prompt, missing_fields)

    if result:
        logger.info(f"Mistral generated {len(result)} CIOMS follow-up questions")
        # For any fields Mistral missed, try generating individually
        missed = [f for f in missing_fields if f not in result]
        if missed:
            for field in missed:
                single_prompt = _build_prompt([field], case_context, language)
                single_result = _call_mistral(single_prompt, [field])
                if single_result and field in single_result:
                    result[field] = single_result[field]
                # If Mistral fails for this field, skip it (no generic fallback)
                else:
                    logger.warning(f"Skipping question for '{field}' — Mistral failed and no fallback")
        return result

    # If Mistral completely fails, return empty — no generic fallback questions
    logger.warning("Mistral API failed — no questions generated (fallback disabled)")
    return {}


def _build_prompt(missing_fields: List[str], case_context: Optional[Dict], language: str = "en") -> str:
    """Build the Mistral prompt for question generation."""
    # Language instruction
    LANGUAGE_NAMES = {
        "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
        "de": "German", "ja": "Japanese", "zh": "Chinese", "pt": "Portuguese",
        "ar": "Arabic",
    }
    lang_name = LANGUAGE_NAMES.get(language, "English")
    lang_instruction = ""
    if language != "en":
        lang_instruction = f"\n\nIMPORTANT: Generate ALL questions in {lang_name} language. The questions must be written entirely in {lang_name}.\n"

    context_str = ""
    if case_context:
        known = {k: str(v) for k, v in case_context.items() if v is not None}
        if known:
            context_str = "\nKnown case information:\n"
            for k, v in known.items():
                context_str += f"- {k.replace('_', ' ')}: {v}\n"

    fields_str = ", ".join(f.replace("_", " ") for f in missing_fields)

    return f"""You are a pharmacovigilance specialist generating follow-up questions for a CIOMS Form-I adverse event report.

The following fields are MISSING and need to be collected from the reporter:
{fields_str}
{context_str}
Generate ONE clear, professional follow-up question for EACH missing field.
Questions should be:
- Direct and specific
- Professional tone appropriate for healthcare reporters
- Context-aware (reference known case details when relevant)
- Each question should help collect the exact missing data point
{lang_instruction}
Return STRICTLY valid JSON mapping field names to questions.
Example format:
{{"field_name": "Your question here?"}}

Field names to use exactly: {json.dumps(missing_fields)}

Output ONLY the JSON object, nothing else."""


def _call_mistral(prompt: str, expected_fields: List[str]) -> Optional[Dict[str, str]]:
    """
    Call Mistral API via existing GeminiClient.
    Returns dict of field → question, or None on failure.
    """
    try:
        from app.agents.gemini_client import get_gemini_client

        client = get_gemini_client()
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3,
        )

        result_text = response.choices[0].message.content
        logger.info(f"Mistral raw response: {result_text[:500]}")

        # Extract JSON from response (may have surrounding text)
        json_match = re.search(r"\{[^{}]*\}", result_text, re.DOTALL)
        if not json_match:
            logger.warning("No JSON object found in Mistral response")
            return None

        parsed = json.loads(json_match.group())

        # Validate: only keep expected field names with string values
        valid = {}
        for field in expected_fields:
            if field in parsed and isinstance(parsed[field], str) and parsed[field].strip():
                valid[field] = parsed[field].strip()

        if valid:
            return valid

        logger.warning("Mistral returned no valid question mappings")
        return None

    except Exception as e:
        logger.error(f"Mistral question generation failed: {e}")
        return None
