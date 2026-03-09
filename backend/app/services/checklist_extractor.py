"""
Checklist Extractor — Converts uploaded checklist PDFs (TAFU, Pregnancy forms)
into structured question items for digital follow-up responses.

Strategy:
1. pdfplumber text extraction + regex parsing (fast, no API cost)
2. Mistral AI fallback if regex yields < 2 items (handles unknown form layouts)

Output: list of dicts matching the follow-up question format:
    {field, field_name, question, criticality, value_score, source}
"""

import re
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def extract_checklist_items(
    file_path: str = None,
    file_bytes: bytes = None,
    document_type: str = "TAFU",
) -> List[Dict[str, str]]:
    """
    Extract checklist items from a PDF and return as structured questions.

    Tries pdfplumber + regex first, falls back to Mistral AI.

    Args:
        file_path: Path to PDF file on disk.
        file_bytes: Raw PDF bytes (alternative to file_path).
        document_type: TAFU or PREGNANCY — used for context in AI fallback.

    Returns:
        List of question dicts:
        [
            {
                "field": "checklist_<index>",
                "field_name": "checklist_<index>",
                "question": "...",
                "criticality": "MEDIUM",
                "value_score": 0.6,
                "source": "checklist_pdf",
                "document_type": "TAFU" | "PREGNANCY",
            }
        ]
    """
    text = _extract_text(file_path=file_path, file_bytes=file_bytes)
    if not text or not text.strip():
        logger.warning("Checklist PDF yielded no text")
        return []

    # Step 1: Try rule-based extraction
    items = _regex_extract(text)

    # Step 2: Mistral fallback if regex found < 2 items
    if len(items) < 2:
        logger.info(
            f"Regex found {len(items)} items — trying Mistral AI extraction"
        )
        ai_items = _mistral_extract(text, document_type)
        if len(ai_items) > len(items):
            items = ai_items

    if not items:
        logger.warning("No checklist items extracted from PDF")
        return []

    # Format as follow-up questions
    questions = []
    for idx, item in enumerate(items):
        clean = item.strip()
        if not clean or len(clean) < 5:
            continue
        # Ensure it ends with a question mark if it doesn't already
        if not clean.endswith("?"):
            clean = clean.rstrip(".") + "?"
        questions.append({
            "field": f"checklist_{document_type.lower()}_{idx + 1}",
            "field_name": f"checklist_{document_type.lower()}_{idx + 1}",
            "question": clean,
            "question_text": clean,  # Email renderer uses this key first
            "criticality": "MEDIUM",
            "value_score": 0.6,
            "source": "checklist_pdf",
            "document_type": document_type,
        })

    logger.info(f"Extracted {len(questions)} checklist items from {document_type} PDF")
    return questions


def _extract_text(file_path: str = None, file_bytes: bytes = None) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber

        if file_bytes:
            import io
            pdf = pdfplumber.open(io.BytesIO(file_bytes))
        elif file_path:
            pdf = pdfplumber.open(file_path)
        else:
            return ""

        pages_text = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
        pdf.close()
        return "\n".join(pages_text)
    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {e}")
        return ""


def _regex_extract(text: str) -> List[str]:
    """
    Rule-based extraction of checklist items from PDF text.

    Handles common patterns:
    - Numbered items: "1. ...", "1) ...", "(1) ..."
    - Checkbox items: "[ ] ...", "[x] ...", "□ ...", "☐ ...", "☑ ..."
    - Bulleted items: "• ...", "- ...", "* ..."
    - Lines ending with "?" (questions)
    - Lines ending with ": ___" or ": ______" (fill-in fields)
    """
    items = []

    # Pattern 1: Numbered items
    numbered = re.findall(
        r'(?:^|\n)\s*(?:\d{1,2}[\.\)]\s*|\(\d{1,2}\)\s*)(.+?)(?=\n|$)',
        text,
        re.MULTILINE,
    )
    items.extend(numbered)

    # Pattern 2: Checkbox items
    checkbox = re.findall(
        r'(?:^|\n)\s*(?:\[[ xX]?\]|□|☐|☑|☒)\s*(.+?)(?=\n|$)',
        text,
        re.MULTILINE,
    )
    items.extend(checkbox)

    # Pattern 3: Bullet items
    bullets = re.findall(
        r'(?:^|\n)\s*[•\-\*]\s+(.+?)(?=\n|$)',
        text,
        re.MULTILINE,
    )
    items.extend(bullets)

    # Pattern 4: Lines that are questions (end with ?)
    questions = re.findall(
        r'(?:^|\n)\s*(.{10,}?\?)\s*(?=\n|$)',
        text,
        re.MULTILINE,
    )
    items.extend(questions)

    # Pattern 5: Fill-in fields (end with : ___ or similar)
    fillin = re.findall(
        r'(?:^|\n)\s*(.{10,}?):\s*_{2,}\s*(?=\n|$)',
        text,
        re.MULTILINE,
    )
    items.extend(fillin)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for item in items:
        clean = item.strip()
        lower = clean.lower()
        if lower not in seen and len(clean) >= 5:
            seen.add(lower)
            unique.append(clean)

    return unique


def _mistral_extract(text: str, document_type: str) -> List[str]:
    """
    Fallback: Use Mistral AI to extract checklist items from PDF text.

    Uses existing GeminiClient (Mistral wrapper).
    """
    try:
        from app.agents.gemini_client import get_gemini_client

        client = get_gemini_client()

        # Truncate text to avoid token limits
        truncated = text[:4000] if len(text) > 4000 else text

        prompt = f"""You are a pharmacovigilance document parser.

Extract ALL checklist items, questions, or fill-in fields from this {document_type} form.

Return ONLY a JSON array of strings, each being one checklist item or question.
Do NOT include headers, titles, or instructions — only actionable items the reporter must answer.

Example output:
["Was the drug discontinued?", "Date of last dose?", "Is the patient pregnant?"]

Document text:
{truncated}

Return ONLY the JSON array, nothing else."""

        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()

        # Parse JSON array from response
        # Handle potential markdown code blocks
        if "```" in raw:
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                raw = match.group(0)

        items = json.loads(raw)
        if isinstance(items, list):
            return [str(i) for i in items if isinstance(i, str) and len(i.strip()) >= 5]

    except Exception as e:
        logger.warning(f"Mistral checklist extraction failed: {e}")

    return []
