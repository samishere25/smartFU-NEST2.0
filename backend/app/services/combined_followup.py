"""
Combined Follow-Up Builder — Aggregates missing-field questions,
reviewer notes, and checklist documents into one structured payload.

Uses ONLY existing logic for AI-generated questions.
Does NOT generate email templates, hardcode content, or simulate sends.

Includes AI-powered conversion of reviewer notes into proper PV follow-up
questions with field mapping, criticality scoring, and professional language.
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from app.models.case import AECase
from app.models.case_document import CaseDocument, DocumentType

logger = logging.getLogger(__name__)


def build_combined_followup(case: AECase, db: Session) -> Dict[str, Any]:
    """
    Consolidated follow-up builder.

    Steps:
    1. Pull AI-generated missing questions (from existing CIOMS question generator).
    2. Pull reviewer questions from REVIEWER_NOTE documents.
    3. Pull checklist documents (TAFU, PREGNANCY).
    4. Combine into one structured payload.

    Returns:
        {
            case_id: str,
            missing_questions: [...],
            reviewer_questions: [...],
            attachments: [{document_type, file_path, file_name}]
        }
    """
    case_id_str = str(case.case_id)
    logger.info(f"Building combined follow-up for case {case_id_str}")

    # ── 1. AI-generated missing-field questions ──
    missing_questions = _get_ai_missing_questions(case, db)

    # ── 2. Reviewer questions from REVIEWER_NOTE documents ──
    reviewer_questions = _get_reviewer_questions(case.case_id, db)

    # ── 3. Checklist attachments (TAFU, PREGNANCY) ──
    attachments = _get_checklist_attachments(case.case_id, db)

    result = {
        "case_id": case_id_str,
        "missing_questions": missing_questions,
        "reviewer_questions": reviewer_questions,
        "attachments": attachments,
    }

    logger.info(
        f"Combined follow-up for {case_id_str}: "
        f"{len(missing_questions)} AI questions, "
        f"{len(reviewer_questions)} reviewer questions, "
        f"{len(attachments)} attachments"
    )

    return result


def _get_ai_missing_questions(case: AECase, db: Session) -> List[Dict[str, str]]:
    """
    Use existing CIOMS question generator to produce AI questions
    for missing fields.

    Source of truth: AECase structured fields + extracted_json from
    the active CIOMS document (if any).
    """
    from app.services.completeness import detect_missing_fields, detect_missing_important_fields
    from app.services.cioms_question_generator import generate_cioms_questions

    # Build case_data from AECase structured fields
    case_data = _aecase_to_cioms_dict(case)

    # Also check the latest active CIOMS document's extracted_json
    cioms_doc = (
        db.query(CaseDocument)
        .filter(
            CaseDocument.case_id == case.case_id,
            CaseDocument.document_type == DocumentType.CIOMS,
            CaseDocument.is_active == True,
        )
        .order_by(CaseDocument.uploaded_at.desc())
        .first()
    )

    if cioms_doc and cioms_doc.extracted_json:
        extracted = cioms_doc.extracted_json
        cioms_fields = extracted.get("cioms_fields", {})
        # Merge: extracted_json fills gaps in AECase fields
        for key, value in cioms_fields.items():
            if value is not None and not case_data.get(key):
                case_data[key] = value

    # Detect missing fields (required + important)
    missing_required = detect_missing_fields(case_data)
    missing_important = detect_missing_important_fields(case_data)
    all_missing = list(set(missing_required + missing_important))

    if not all_missing:
        return []

    # Generate AI questions using existing CIOMS question generator
    case_context = {k: v for k, v in case_data.items() if v is not None}
    questions_map = generate_cioms_questions(all_missing, case_context)

    # Structure the output
    result = []
    for field, question_text in questions_map.items():
        result.append({
            "field_name": field,
            "question": question_text,
            "is_required": field in missing_required,
            "source": "ai_generated",
        })

    return result


def _get_reviewer_questions(case_id, db: Session) -> List[Dict[str, Any]]:
    """
    Extract reviewer questions from REVIEWER_NOTE documents.

    Reads the extracted_json field if populated; otherwise returns
    metadata-only entries so the frontend knows there are reviewer notes.
    """
    reviewer_docs = (
        db.query(CaseDocument)
        .filter(
            CaseDocument.case_id == case_id,
            CaseDocument.document_type == DocumentType.REVIEWER_NOTE,
            CaseDocument.is_active == True,
        )
        .order_by(CaseDocument.uploaded_at.desc())
        .all()
    )

    questions = []
    for doc in reviewer_docs:
        if doc.extracted_json and isinstance(doc.extracted_json, dict):
            # If the reviewer uploaded structured JSON with questions
            items = doc.extracted_json.get("questions", [])
            for item in items:
                questions.append({
                    "question": item if isinstance(item, str) else str(item),
                    "source": "reviewer_note",
                    "document_id": str(doc.id),
                    "file_name": doc.file_name,
                    "uploaded_by": doc.uploaded_by,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                })
        else:
            # Plain file — note its existence
            questions.append({
                "question": None,
                "source": "reviewer_note",
                "document_id": str(doc.id),
                "file_name": doc.file_name,
                "uploaded_by": doc.uploaded_by,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "note": "Document uploaded — review contents manually.",
            })

    return questions


def _get_checklist_attachments(case_id, db: Session) -> List[Dict[str, str]]:
    """
    Pull TAFU and PREGNANCY checklist documents as attachments.

    These are NOT read or modified by AI — just listed for inclusion
    in the consolidated follow-up.
    """
    types = [DocumentType.TAFU, DocumentType.PREGNANCY]
    docs = (
        db.query(CaseDocument)
        .filter(
            CaseDocument.case_id == case_id,
            CaseDocument.document_type.in_(types),
            CaseDocument.is_active == True,
        )
        .order_by(CaseDocument.uploaded_at.desc())
        .all()
    )

    return [
        {
            "document_type": doc.document_type.value,
            "file_name": doc.file_name,
            "file_path": doc.file_path,
            "document_id": str(doc.id),
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        }
        for doc in docs
    ]


def get_supplementary_questions(
    case: AECase, db: Session, existing_fields: set = None
) -> Dict[str, Any]:
    """
    Get reviewer questions + checklist items formatted for FollowUpTrigger.

    Called from cases.py BEFORE trigger_automated_followup() to merge
    supplementary questions into the filtered_questions list.

    Args:
        case: The AECase being analyzed.
        db: Database session.
        existing_fields: Set of field names already in filtered_questions
                         (to avoid duplicates).

    Returns:
        {
            "reviewer_questions": [...],   # trigger-compatible format
            "checklist_questions": [...],   # trigger-compatible format
            "attachments": [...],           # file metadata for response_data
        }
    """
    existing_fields = existing_fields or set()

    # ── 1. Reviewer questions → trigger format ──
    raw_reviewer = _get_reviewer_questions(case.case_id, db)
    reviewer_questions = []
    for idx, rq in enumerate(raw_reviewer):
        q_text = rq.get("question")
        if not q_text:
            continue  # Skip metadata-only entries (no actual question)
        field_name = f"reviewer_q_{idx + 1}"
        if field_name in existing_fields:
            continue
        reviewer_questions.append({
            "field": field_name,
            "field_name": field_name,
            "question": q_text,
            "question_text": q_text,  # Email renderer uses this key first
            "criticality": "HIGH",        # Reviewer questions are high priority
            "value_score": 0.85,
            "source": "reviewer_note",
            "reviewer_override": True,     # Mark as reviewer-added (not AI)
        })

    # ── 2. Checklist PDFs → web form questions ──
    checklist_questions = _extract_checklist_questions(case.case_id, db, existing_fields)

    # ── 3. Attachments (original PDFs — sent unmodified) ──
    attachments = _get_checklist_attachments(case.case_id, db)

    logger.info(
        f"Supplementary for case {case.case_id}: "
        f"{len(reviewer_questions)} reviewer, "
        f"{len(checklist_questions)} checklist items, "
        f"{len(attachments)} attachments"
    )

    return {
        "reviewer_questions": reviewer_questions,
        "checklist_questions": checklist_questions,
        "attachments": attachments,
    }


def _extract_checklist_questions(
    case_id, db: Session, existing_fields: set
) -> List[Dict[str, Any]]:
    """
    Extract checklist items from TAFU/PREGNANCY PDFs and convert to
    trigger-compatible question format.

    Uses checklist_extractor.py (pdfplumber + Mistral fallback).
    """
    from app.services.checklist_extractor import extract_checklist_items

    types = [DocumentType.TAFU, DocumentType.PREGNANCY]
    docs = (
        db.query(CaseDocument)
        .filter(
            CaseDocument.case_id == case_id,
            CaseDocument.document_type.in_(types),
            CaseDocument.is_active == True,
        )
        .order_by(CaseDocument.uploaded_at.desc())
        .all()
    )

    all_questions = []
    for doc in docs:
        try:
            items = extract_checklist_items(
                file_path=doc.file_path,
                document_type=doc.document_type.value,
            )
            for item in items:
                if item.get("field") not in existing_fields:
                    all_questions.append(item)
        except Exception as e:
            logger.warning(
                f"Checklist extraction failed for doc {doc.id} "
                f"({doc.file_name}): {e}"
            )

    return all_questions


def convert_reviewer_notes_to_questions(
    notes: List[str],
    case_data: Dict[str, Any],
    existing_questions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert reviewer notes into proper PV follow-up questions using Mistral LLM.

    Reviewer notes are free-text hints like "check concomitant medications" or
    "verify therapy duration". This function uses AI to:
    - Convert each note into a professional, context-aware follow-up question
    - Auto-detect the relevant CIOMS field name
    - Assign criticality based on note content + case context
    - Deduplicate against existing AI-generated questions

    Args:
        notes: List of reviewer free-text notes.
        case_data: Dict with known case fields for context.
        existing_questions: List of already-generated questions (for dedup).

    Returns:
        List of dicts: {field_name, question, criticality, source, original_note}
    """
    if not notes:
        return []

    # Build context for the LLM
    existing_q_texts = [
        q.get("question_text") or q.get("question", "")
        for q in existing_questions
    ]
    existing_fields = [
        q.get("field_name") or q.get("field", "")
        for q in existing_questions
    ]

    case_context_str = ""
    if case_data:
        known = {k: str(v) for k, v in case_data.items() if v is not None}
        if known:
            case_context_str = "\nKnown case information:\n"
            for k, v in list(known.items())[:15]:  # Limit context size
                case_context_str += f"- {k.replace('_', ' ')}: {v}\n"

    existing_q_str = ""
    if existing_q_texts:
        existing_q_str = "\nExisting AI-generated questions (DO NOT duplicate these):\n"
        for i, q in enumerate(existing_q_texts[:20], 1):
            existing_q_str += f"  {i}. {q}\n"

    notes_str = "\n".join(f"  {i+1}. {note}" for i, note in enumerate(notes))

    prompt = f"""You are a pharmacovigilance specialist. A medical reviewer has added the following notes about what additional information is needed for an adverse event case. Convert each note into a proper, professional follow-up question.
{case_context_str}
Reviewer notes to convert:
{notes_str}
{existing_q_str}
For EACH reviewer note, generate:
1. field_name: The most relevant CIOMS field (e.g., concomitant_drugs, therapy_duration, dose, medical_history, reaction_onset, dechallenge, rechallenge, outcome, etc.)
2. question: A clear, professional follow-up question in proper medical language
3. criticality: One of CRITICAL, HIGH, MEDIUM, LOW based on safety impact

Rules:
- Questions must be professional and suitable for healthcare reporter communication
- Do NOT duplicate any existing AI-generated questions listed above
- If a note is vague, still generate the best possible question
- Each question should collect specific, actionable data

Return STRICTLY valid JSON as an array of objects.
Example format:
[{{"field_name": "concomitant_drugs", "question": "Could you provide a complete list of all medications the patient was taking at the time of the adverse event?", "criticality": "HIGH", "original_note": "check concomitant medications"}}]

Output ONLY the JSON array, nothing else."""

    result = _call_mistral_for_notes(prompt, len(notes))

    if result:
        # Tag each question with source
        for item in result:
            item["source"] = "REVIEWER_NOTE_AI"
        logger.info(f"Converted {len(result)} reviewer notes into AI questions")
        return result

    # Fallback: if LLM fails, create basic questions from notes directly
    logger.warning("Mistral note conversion failed — using notes as-is")
    fallback = []
    for i, note in enumerate(notes):
        fallback.append({
            "field_name": f"reviewer_note_{i+1}",
            "question": note,
            "question_text": note,  # Email renderer uses this key first
            "criticality": "HIGH",
            "source": "REVIEWER_NOTE_RAW",
            "original_note": note,
        })
    return fallback


def _call_mistral_for_notes(prompt: str, expected_count: int) -> Optional[List[Dict]]:
    """
    Call Mistral API to convert reviewer notes to questions.
    Returns list of question dicts, or None on failure.
    """
    try:
        from app.agents.gemini_client import get_gemini_client

        client = get_gemini_client()
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3,
        )

        result_text = response.choices[0].message.content
        logger.info(f"Mistral notes response: {result_text[:500]}")

        # Extract JSON array from response
        json_match = re.search(r"\[[\s\S]*\]", result_text)
        if not json_match:
            logger.warning("No JSON array found in Mistral note conversion response")
            return None

        parsed = json.loads(json_match.group())

        if not isinstance(parsed, list):
            logger.warning("Mistral returned non-array JSON for note conversion")
            return None

        # Validate each item
        valid = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            if not item.get("question") or not isinstance(item["question"], str):
                continue
            q_text = item["question"].strip()
            valid.append({
                "field_name": item.get("field_name", "reviewer_custom"),
                "question": q_text,
                "question_text": q_text,  # Email renderer uses this key first
                "criticality": item.get("criticality", "HIGH").upper(),
                "original_note": item.get("original_note", ""),
            })

        return valid if valid else None

    except Exception as e:
        logger.error(f"Mistral note conversion failed: {e}")
        return None


def _aecase_to_cioms_dict(case: AECase) -> dict:
    """
    Map AECase structured fields back to the 24-field CIOMS dict
    used by the completeness checker.
    """
    return {
        "patient_initials": case.patient_initials,
        "age": case.patient_age,
        "sex": case.patient_sex,
        "country": case.reporter_country,
        "reaction_description": case.adverse_event,
        "reaction_onset": str(case.event_date) if case.event_date else None,
        "seriousness": case.is_serious,
        "outcome": case.event_outcome,
        "suspect_drug_name": case.suspect_drug,
        "dose": case.drug_dose,
        "route": case.drug_route,
        "indication": case.indication,
        "therapy_start": str(case.therapy_start) if case.therapy_start else None,
        "therapy_end": str(case.therapy_end) if case.therapy_end else None,
        "therapy_duration": case.therapy_duration,
        "dechallenge": case.dechallenge,
        "rechallenge": case.rechallenge,
        "concomitant_drugs": case.concomitant_drugs,
        "medical_history": case.medical_history,
        "report_source": case.reporter_type,
        "report_type": case.report_type,
        "reporter_email": case.reporter_email,
        "reporter_phone": case.reporter_phone,
        "manufacturer_name": case.manufacturer_name,
    }
