"""
CIOMS Combined Send — Merges CIOMS missing-field questions + repo form
questions + reviewer AI-converted notes into one follow-up, with repo
form PDFs attached.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.case import AECase
from app.models.repo_document import RepoDocument
from app.schemas.repo_document import CiomsCombinedSendRequest

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_active_user)])


def _find_case(case_id: str, db: Session) -> AECase:
    """Find case by UUID or by numeric primaryid."""
    # Try UUID first
    try:
        uid = UUID(case_id)
        case = db.query(AECase).filter(AECase.case_id == uid).first()
        if case:
            return case
    except (ValueError, AttributeError):
        pass

    # Try numeric primaryid
    try:
        pid = int(case_id)
        case = db.query(AECase).filter(AECase.primaryid == pid).first()
        if case:
            return case
    except (ValueError, TypeError):
        pass

    raise HTTPException(status_code=404, detail=f"Case {case_id} not found")


def _aecase_to_dict(case: AECase) -> dict:
    """Build case_data dict for AI question generation context."""
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


@router.post("/{case_id}/cioms-combined-send")
async def cioms_combined_send(
    case_id: str,
    body: CiomsCombinedSendRequest,
    db: Session = Depends(get_db),
):
    """
    Send combined follow-up: CIOMS missing fields + repo form questions
    + reviewer AI-converted notes + repo form PDF attachments.
    """
    case = _find_case(case_id, db)
    case_data = _aecase_to_dict(case)
    case_context = {k: v for k, v in case_data.items() if v is not None}

    all_questions = []
    seen_texts = set()

    def _add_questions(items, source_tag):
        for item in items:
            q_text = item.get("question", "")
            if q_text and q_text.lower() not in seen_texts:
                seen_texts.add(q_text.lower())
                item["source"] = source_tag
                all_questions.append(item)

    # ── 1. CIOMS missing-field questions (AI-generated) ──
    if body.cioms_missing_fields:
        try:
            from app.services.cioms_question_generator import generate_cioms_questions

            questions_map = generate_cioms_questions(body.cioms_missing_fields, case_context)
            cioms_items = [
                {
                    "field": field,
                    "field_name": field,
                    "question": q_text,
                    "criticality": "HIGH",
                    "value_score": 0.8,
                }
                for field, q_text in questions_map.items()
            ]
            _add_questions(cioms_items, "CIOMS_MISSING")
            logger.info(f"Generated {len(cioms_items)} CIOMS questions for case {case_id}")
        except Exception as e:
            logger.error(f"CIOMS question generation failed: {e}")

    # ── 2. Repo form questions (pre-extracted, zero AI calls) ──
    attachments = []
    if body.repo_doc_ids:
        for doc_id in body.repo_doc_ids:
            doc = db.query(RepoDocument).filter(
                RepoDocument.id == doc_id,
                RepoDocument.is_active == True,
            ).first()
            if not doc:
                logger.warning(f"Repo document {doc_id} not found, skipping")
                continue

            # Load pre-extracted questions
            if doc.extracted_questions and isinstance(doc.extracted_questions, list):
                _add_questions(doc.extracted_questions, "REPO_FORM")

            # Add PDF as attachment
            attachments.append({
                "document_type": doc.form_type,
                "file_name": doc.file_name,
                "file_path": doc.file_path,
                "document_id": str(doc.id),
            })

        logger.info(f"Loaded questions from {len(body.repo_doc_ids)} repo forms, {len(attachments)} attachments")

    # ── 3. Reviewer notes → AI-converted questions ──
    if body.reviewer_notes and body.reviewer_notes.strip():
        try:
            from app.services.combined_followup import convert_reviewer_notes_to_questions

            notes = [n.strip() for n in body.reviewer_notes.strip().split("\n") if n.strip()]
            if notes:
                reviewer_items = convert_reviewer_notes_to_questions(
                    notes=notes,
                    case_data=case_data,
                    existing_questions=all_questions,
                )
                _add_questions(reviewer_items, "REVIEWER_NOTE_AI")
                logger.info(f"Converted {len(notes)} reviewer notes into {len(reviewer_items)} questions")
        except Exception as e:
            logger.error(f"Reviewer note conversion failed: {e}")

    if not all_questions:
        raise HTTPException(
            status_code=400,
            detail="No questions to send. Select repo forms, add reviewer notes, or ensure CIOMS fields are missing.",
        )

    # ── 4. Build analysis_result for trigger ──
    analysis_result = {
        "followup_required": True,
        "decision": "PROCEED",
        "risk_score": case.seriousness_score or 0.0,
        "completeness_score": case.data_completeness_score or 0.0,
        "response_probability": 0.5,
        "stop_followup": False,
        "followup_channel": "MULTI",
    }

    if attachments:
        analysis_result["followup_attachments"] = attachments

    # ── 5. Send via multi-channel trigger ──
    from app.services.followup_trigger import FollowUpTrigger

    followup_result = await FollowUpTrigger.trigger_automated_followup(
        db=db,
        case=case,
        analysis_result=analysis_result,
        questions=all_questions,
        user_id=None,
    )

    # ── 6. Audit log ──
    try:
        from app.services.audit_service import AuditService
        AuditService.log_action(
            db=db,
            action="CIOMS_COMBINED_SEND",
            entity_type="case",
            entity_id=str(case.case_id),
            details={
                "cioms_questions": len([q for q in all_questions if q.get("source") == "CIOMS_MISSING"]),
                "repo_form_questions": len([q for q in all_questions if q.get("source") == "REPO_FORM"]),
                "reviewer_questions": len([q for q in all_questions if q.get("source") == "REVIEWER_NOTE_AI"]),
                "attachments": len(attachments),
                "repo_doc_ids": [str(d) for d in body.repo_doc_ids],
            },
        )
    except Exception as e:
        logger.warning(f"Audit logging failed: {e}")

    return {
        "success": True,
        "case_id": str(case.case_id),
        "total_questions": len(all_questions),
        "breakdown": {
            "cioms_missing": len([q for q in all_questions if q.get("source") == "CIOMS_MISSING"]),
            "repo_form": len([q for q in all_questions if q.get("source") == "REPO_FORM"]),
            "reviewer_ai": len([q for q in all_questions if q.get("source") == "REVIEWER_NOTE_AI"]),
        },
        "attachments_count": len(attachments),
        "followup_result": followup_result,
    }
