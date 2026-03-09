"""
Repo Question Filter — Mistral AI-based smart filtering.

Given a list of repo form questions (e.g., 63 from a TAFU checklist) and
the missing fields identified by the completeness service, uses Mistral AI
to pick only the 5-15 questions that are most relevant to the current case.

This avoids sending all 63 questions to the reporter, which would be
overwhelming and reduce response rates.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def filter_repo_questions_for_case(
    repo_questions: List[Dict[str, Any]],
    missing_fields: List[Dict[str, Any]],
    case_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Use Mistral AI to select the most relevant repo form questions
    for a case based on its missing fields.

    Args:
        repo_questions: Full list of questions from the repo document(s).
                        Each dict has at least 'question_text' and 'field_name'.
        missing_fields: List of missing field dicts from DataCompletenessService
                        (each has 'field', 'criticality', 'category', etc.).
        case_context:   Optional known case data for additional context.

    Returns:
        Filtered list of repo questions (5-15 items), each annotated with
        'relevance_reason' from the AI.
    """
    if not repo_questions:
        return []

    # If there are very few questions, no need to filter
    if len(repo_questions) <= 10:
        logger.info(f"Only {len(repo_questions)} repo questions — returning all (no filter needed)")
        for q in repo_questions:
            q.setdefault("source", "REPO_FORM_AI_FILTERED")
            q.setdefault("criticality", "HIGH")
            # Ensure question_text is set (email renderer uses this key first)
            if "question_text" not in q and "question" in q:
                q["question_text"] = q["question"]
            elif "question_text" not in q and "text" in q:
                q["question_text"] = q["text"]
        return repo_questions

    # If there are NO missing fields (case 100% complete on core fields),
    # the AI filter would return 0 questions since there's nothing to match.
    # In this case, return all repo questions directly — they were selected
    # by the user explicitly, so they should all be sent.
    if not missing_fields or len(missing_fields) == 0:
        logger.info(f"No missing fields — returning all {len(repo_questions)} repo questions (user-selected)")
        for q in repo_questions:
            q.setdefault("source", "REPO_FORM_AI_FILTERED")
            q.setdefault("criticality", "HIGH")
            if "question_text" not in q and "question" in q:
                q["question_text"] = q["question"]
            elif "question_text" not in q and "text" in q:
                q["question_text"] = q["text"]
        return repo_questions

    # Build Mistral prompt
    prompt = _build_filter_prompt(repo_questions, missing_fields, case_context)
    selected = _call_mistral_filter(prompt, len(repo_questions))

    if selected is None:
        # Fallback: return first 10 questions
        logger.warning("Mistral filter failed — returning first 10 questions as fallback")
        return repo_questions[:10]

    # Map selected indices back to original questions
    filtered = []
    for item in selected:
        idx = item.get("index")
        if idx is not None and 0 <= idx < len(repo_questions):
            q = repo_questions[idx].copy()
            q["relevance_reason"] = item.get("reason", "AI-selected as relevant")
            q["source"] = "REPO_FORM_AI_FILTERED"
            filtered.append(q)

    if not filtered:
        logger.warning("Mistral returned no valid indices — returning all repo questions")
        for q in repo_questions:
            q.setdefault("source", "REPO_FORM_AI_FILTERED")
            q.setdefault("criticality", "HIGH")
            if "question_text" not in q and "question" in q:
                q["question_text"] = q["question"]
            elif "question_text" not in q and "text" in q:
                q["question_text"] = q["text"]
        return repo_questions

    # Ensure filtered questions have standardized keys
    for q in filtered:
        q.setdefault("source", "REPO_FORM_AI_FILTERED")
        q.setdefault("criticality", "HIGH")
        if "question_text" not in q and "question" in q:
            q["question_text"] = q["question"]
        elif "question_text" not in q and "text" in q:
            q["question_text"] = q["text"]

    logger.info(
        f"✅ Mistral filtered {len(repo_questions)} repo questions down to {len(filtered)}"
    )
    return filtered


def _build_filter_prompt(
    repo_questions: List[Dict],
    missing_fields: List[Dict],
    case_context: Optional[Dict],
) -> str:
    """Build the Mistral prompt for question filtering."""

    # Format missing fields
    missing_str = ""
    if missing_fields:
        missing_str = "\nMISSING FIELDS in this case (need follow-up):\n"
        for mf in missing_fields:
            field = mf.get("field", "unknown")
            crit = mf.get("criticality", "MEDIUM")
            missing_str += f"  - {field} [{crit}]\n"

    # Format case context
    context_str = ""
    if case_context:
        known = {k: str(v) for k, v in case_context.items() if v is not None and str(v).strip()}
        if known:
            context_str = "\nKNOWN CASE DATA:\n"
            for k, v in known.items():
                context_str += f"  - {k}: {v}\n"

    # Format questions with indices
    questions_str = ""
    for i, q in enumerate(repo_questions):
        text = q.get("question_text", q.get("text", "N/A"))
        field = q.get("field_name", "")
        questions_str += f"  [{i}] {text}"
        if field:
            questions_str += f"  (field: {field})"
        questions_str += "\n"

    return f"""You are a pharmacovigilance specialist reviewing follow-up questions for an adverse event case.

Below is a list of {len(repo_questions)} questions from a standardized repository form (TAFU checklist).
NOT ALL of these are relevant to this specific case. Your task is to select ONLY the 5-15 questions
that are most relevant given the missing data and case context.

{missing_str}
{context_str}

ALL REPO FORM QUESTIONS (indexed):
{questions_str}

SELECTION CRITERIA:
1. Prioritize questions that directly address MISSING FIELDS (especially CRITICAL ones).
2. Include questions about drug details, patient demographics, and event timeline if those are missing.
3. Exclude questions about data already known (see KNOWN CASE DATA above).
4. Exclude questions that are generic administrative or duplicative of AI-generated questions.
5. Select between 5 and 15 questions total.

Return STRICTLY valid JSON — an array of objects with "index" (integer) and "reason" (short string):
[
  {{"index": 3, "reason": "Addresses missing patient age"}},
  {{"index": 7, "reason": "Collects drug dose information"}}
]

Output ONLY the JSON array, nothing else."""


def _call_mistral_filter(prompt: str, total_questions: int) -> Optional[List[Dict]]:
    """
    Call Mistral AI to filter repo questions.
    Returns list of {index, reason} dicts, or None on failure.
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
        logger.info(f"Mistral filter raw response: {result_text[:500]}")

        # Extract JSON array from response
        json_match = re.search(r"\[.*\]", result_text, re.DOTALL)
        if not json_match:
            logger.warning("No JSON array found in Mistral filter response")
            return None

        parsed = json.loads(json_match.group())

        if not isinstance(parsed, list):
            logger.warning("Mistral filter response is not a list")
            return None

        # Validate entries
        valid = []
        for item in parsed:
            if isinstance(item, dict) and "index" in item:
                idx = item["index"]
                if isinstance(idx, int) and 0 <= idx < total_questions:
                    valid.append({
                        "index": idx,
                        "reason": str(item.get("reason", "AI-selected")),
                    })

        if not valid:
            logger.warning("Mistral filter returned no valid indices")
            return None

        # Enforce 5-15 cap
        if len(valid) > 15:
            valid = valid[:15]

        return valid

    except Exception as e:
        logger.error(f"Mistral repo question filter failed: {e}")
        return None
