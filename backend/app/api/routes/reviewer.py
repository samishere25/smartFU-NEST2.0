"""
Novartis Review Dashboard Routes — Case review, clinical summary,
manual follow-up trigger, and reviewer decisions.

Additive only. Does NOT modify:
- Orchestration (graph.py)
- ML risk model
- Lifecycle tracker schema
- Communication service
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.user import User
from app.models.case import AECase
from app.models.followup import FollowUpAttempt, FollowUpDecision, FollowUpResponse, FieldUpdateHistory
from app.core.security import get_current_active_user
from app.services.audit_service import AuditService

router = APIRouter()
logger = logging.getLogger(__name__)

# Statuses that indicate a case has already been actioned by a reviewer
_POST_REVIEW_STATUSES = {"REVIEWER_APPROVED", "CLOSED"}


# ── Schemas ──────────────────────────────────────────────────

class ReviewerDecisionRequest(BaseModel):
    decision: str  # APPROVE | REQUEST_MORE_INFO | ESCALATE | CLOSE
    reviewer_comment: Optional[str] = None


class ReviewerDecisionResponse(BaseModel):
    success: bool
    case_id: str
    decision: str
    previous_status: str
    new_status: str
    reviewer: str
    timestamp: str
    message: str


# ── Helpers ──────────────────────────────────────────────────

def _find_case(case_id: str, db: Session) -> AECase:
    """Find case by primaryid or UUID."""
    case = None
    try:
        case = db.query(AECase).filter(AECase.primaryid == int(case_id)).first()
    except (ValueError, TypeError):
        pass
    if not case:
        try:
            case = db.query(AECase).filter(AECase.case_id == UUID(case_id)).first()
        except (ValueError, TypeError):
            pass
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found.",
        )
    return case


def _build_case_summary(case: AECase) -> dict:
    """Build structured case summary for reviewer."""
    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "patient": {
            "age": case.patient_age,
            "sex": case.patient_sex,
            "initials": getattr(case, "patient_initials", None),
            "medical_history": getattr(case, "medical_history", None),
        },
        "drug": {
            "suspect_drug": case.suspect_drug,
            "dose": case.drug_dose,
            "route": case.drug_route,
            "indication": getattr(case, "indication", None),
            "concomitant_drugs": getattr(case, "concomitant_drugs", None),
        },
        "event": {
            "adverse_event": case.adverse_event,
            "event_date": case.event_date.isoformat() if case.event_date else None,
            "event_outcome": case.event_outcome,
        },
        "reporter": {
            "reporter_type": case.reporter_type,
            "country": case.reporter_country,
            "email": getattr(case, "reporter_email", None),
            "phone": getattr(case, "reporter_phone", None),
        },
        "assessment": {
            "is_serious": case.is_serious,
            "seriousness_score": case.seriousness_score,
            "data_completeness_score": case.data_completeness_score,
            "risk_level": case.risk_level,
            "case_priority": case.case_priority,
        },
        "status": {
            "case_status": case.case_status,
            "requires_followup": case.requires_followup,
            "human_reviewed": case.human_reviewed,
            "reviewed_by": case.reviewed_by,
            "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
            "review_notes": case.review_notes,
        },
        "intake": {
            "intake_source": case.intake_source,
            "source_filename": case.source_filename,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        },
    }


def _build_followup_timeline(case_id, db: Session) -> dict:
    """Build follow-up timeline for reviewer with full detail."""
    attempts = (
        db.query(FollowUpAttempt)
        .filter(FollowUpAttempt.case_id == case_id)
        .order_by(FollowUpAttempt.created_at.asc())
        .all()
    )

    timeline = []
    for a in attempts:
        questions_count = 0
        questions_list = []
        if a.response_data and isinstance(a.response_data, dict):
            questions_list = a.response_data.get("questions", [])
            questions_count = len(questions_list)

        # Get responses for this attempt
        responses = (
            db.query(FollowUpResponse)
            .filter(FollowUpResponse.attempt_id == a.attempt_id)
            .order_by(FollowUpResponse.responded_at.asc())
            .all()
        )
        response_list = []
        for r in responses:
            response_list.append({
                "response_id": str(r.response_id),
                "field_name": r.field_name,
                "question_text": r.question_text,
                "response_text": r.response_text,
                "field_value": r.field_value,
                "previous_value": r.previous_value,
                "channel": r.channel,
                "is_complete": r.is_complete,
                "is_validated": r.is_validated,
                "processed": r.processed,
                "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            })

        timeline.append({
            "attempt_id": str(a.attempt_id),
            "decision_id": str(a.decision_id) if a.decision_id else None,
            "channel": a.channel,
            "status": a.status,
            "questions_count": questions_count,
            "questions": questions_list,
            "responses": response_list,
            "responses_count": len(response_list),
            "questions_answered": a.questions_answered or len(response_list),
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
            "sent_to": a.sent_to,
            "responded_at": a.responded_at.isoformat() if a.responded_at else None,
            "iteration_number": a.iteration_number,
            "stop_reason": a.stop_reason,
        })

    # Compute answered vs pending vs missing
    all_questions_sent = set()
    all_questions_answered = set()
    for t in timeline:
        for q in t.get("questions", []):
            field = q.get("field") or q.get("field_name")
            if field:
                all_questions_sent.add(field)
        for r in t.get("responses", []):
            if r.get("field_value"):
                all_questions_answered.add(r["field_name"])

    still_missing = all_questions_sent - all_questions_answered

    return {
        "total_attempts": len(attempts),
        "pending": sum(1 for a in attempts if a.status in ("PENDING", "SENT", "AWAITING_RESPONSE")),
        "responded": sum(1 for a in attempts if a.status in ("RESPONDED", "PARTIAL_RESPONSE")),
        "expired": sum(1 for a in attempts if a.status == "EXPIRED"),
        "failed": sum(1 for a in attempts if a.status == "FAILED"),
        "total_questions_sent": len(all_questions_sent),
        "total_questions_answered": len(all_questions_answered),
        "still_missing_fields": list(still_missing),
        "timeline": timeline,
    }


def _build_narrative(case: AECase) -> str:
    """Auto-generate a clinical narrative from case data."""
    parts = []

    # Patient
    age_str = f"{case.patient_age}-year-old" if case.patient_age else "Patient of unknown age"
    sex_str = case.patient_sex or "unknown sex"
    parts.append(f"{age_str} ({sex_str})")

    # Medical history
    history = getattr(case, "medical_history", None)
    if history:
        parts.append(f"with medical history of {history}")

    # Drug
    parts.append(f"was treated with {case.suspect_drug}")
    indication = getattr(case, "indication", None)
    if indication:
        parts.append(f"for {indication}")
    if case.drug_dose:
        parts.append(f"at {case.drug_dose}")
    if case.drug_route:
        parts.append(f"via {case.drug_route} route")

    # Event
    parts.append(f"and developed {case.adverse_event}")
    if case.event_date:
        parts.append(f"on {case.event_date.strftime('%Y-%m-%d')}")

    # Outcome
    if case.event_outcome:
        outcome_map = {
            "DE": "resulting in death",
            "LT": "which was life-threatening",
            "HO": "requiring hospitalization",
            "DS": "resulting in disability",
            "CA": "associated with congenital anomaly",
            "RI": "requiring medical intervention",
            "OT": "with other outcome",
            "NS": "outcome not specified",
        }
        outcome_text = outcome_map.get(case.event_outcome.upper(), f"with outcome: {case.event_outcome}")
        parts.append(outcome_text)

    # Seriousness
    if case.is_serious:
        parts.append("(classified as SERIOUS)")

    narrative = " ".join(parts) + "."
    return narrative


def _get_regulatory_seriousness(case: AECase) -> dict:
    """Run regulatory seriousness evaluation."""
    try:
        from app.services.regulatory_seriousness import evaluate_regulatory_seriousness
        return evaluate_regulatory_seriousness({
            "event_outcome": case.event_outcome,
            "adverse_event": case.adverse_event,
            "medical_history": getattr(case, "medical_history", None),
            "is_serious": case.is_serious,
        })
    except Exception:
        return {"is_serious": case.is_serious, "seriousness_criteria": [], "seriousness_source": "fallback"}


# ── Endpoints ────────────────────────────────────────────────

@router.get("/cases")
async def list_review_cases(
    skip: int = 0,
    limit: int = 50,
    risk_level: str = None,
    status_filter: str = None,
    drug: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Review queue — paginated list of cases ready for reviewer attention.

    Supports skip/limit pagination and optional filters.
    """
    query = (
        db.query(AECase)
        .filter(AECase.case_status.notin_(_POST_REVIEW_STATUSES))
    )

    # Optional filters
    if risk_level:
        query = query.filter(AECase.risk_level == risk_level.upper())
    if status_filter:
        query = query.filter(AECase.case_status == status_filter)
    if drug:
        query = query.filter(AECase.suspect_drug.ilike(f"%{drug}%"))

    total = query.count()

    cases = (
        query
        .order_by(desc(AECase.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for c in cases:
        result.append({
            "case_id": str(c.case_id),
            "primaryid": c.primaryid,
            "suspect_drug": c.suspect_drug,
            "reaction": c.adverse_event,
            "is_serious": c.is_serious,
            "ml_risk_score": c.seriousness_score,
            "risk_level": c.risk_level,
            "final_risk_decision": c.case_priority,
            "days_remaining": None,
            "reporter_type": c.reporter_type,
            "date_received": c.created_at.isoformat() if c.created_at else None,
            "case_status": c.case_status,
            "intake_source": c.intake_source,
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "page": skip // limit + 1,
        "total_pages": (total + limit - 1) // limit,
        "cases": result,
    }


@router.get("/{case_id}")
async def get_review_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Reviewer dashboard — Full case overview for medical review.

    Returns structured response including:
    - Case summary (patient, drug, event, reporter)
    - Follow-up timeline (attempts, reminders, status)
    - Auto-generated clinical narrative
    - ML risk score
    - Regulatory seriousness (deterministic)
    - Lifecycle status
    """
    case = _find_case(case_id, db)

    # Case summary
    summary = _build_case_summary(case)

    # Follow-up timeline
    followup_timeline = _build_followup_timeline(case.case_id, db)

    # Auto-generated narrative
    narrative = _build_narrative(case)

    # Regulatory seriousness (deterministic)
    regulatory = _get_regulatory_seriousness(case)

    # ML risk assessment
    ml_risk = {
        "seriousness_score": case.seriousness_score,
        "risk_level": case.risk_level,
        "priority_score": case.priority_score,
        "note": "ML risk controls prioritization only — not regulatory seriousness",
    }

    # Lifecycle status (if available)
    lifecycle_status = None
    try:
        from app.services.lifecycle_db_service import LifecycleDBService
        lifecycle_service = LifecycleDBService(db)
        lifecycle = lifecycle_service.get_lifecycle_by_case_id(str(case.case_id))
        if lifecycle:
            lifecycle_status = lifecycle_service.get_lifecycle_summary(lifecycle)
    except Exception:
        pass

    # Combined follow-up package (built on-demand, NOT sent)
    combined_package = None
    try:
        from app.services.combined_followup import build_combined_followup
        combined_package = build_combined_followup(case, db)
    except Exception as cf_err:
        logger.warning(f"Combined package build failed (non-blocking): {cf_err}")

    # Case documents / attachments
    attachments = []
    try:
        from app.models.case_document import CaseDocument
        docs = (
            db.query(CaseDocument)
            .filter(CaseDocument.case_id == case.case_id, CaseDocument.is_active == True)
            .order_by(CaseDocument.uploaded_at.desc())
            .all()
        )
        for doc in docs:
            attachments.append({
                "id": str(doc.id),
                "document_type": doc.document_type.value if doc.document_type else None,
                "file_name": doc.file_name,
                "uploaded_by": doc.uploaded_by,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            })
    except Exception:
        pass

    # ── Reporter Responses (all channels) ────────────────────
    reporter_responses = []
    try:
        all_responses = (
            db.query(FollowUpResponse)
            .filter(FollowUpResponse.case_id == case.case_id)
            .order_by(FollowUpResponse.responded_at.asc())
            .all()
        )
        for r in all_responses:
            reporter_responses.append({
                "response_id": str(r.response_id),
                "attempt_id": str(r.attempt_id) if r.attempt_id else None,
                "field_name": r.field_name,
                "question_text": r.question_text,
                "response_text": r.response_text,
                "field_value": r.field_value,
                "previous_value": r.previous_value,
                "channel": r.channel,
                "attempt_number": r.attempt_number,
                "is_complete": r.is_complete,
                "is_validated": r.is_validated,
                "processed": r.processed,
                "needs_clarification": r.needs_clarification,
                "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            })
    except Exception:
        pass

    # ── Field Update History (old→new) ───────────────────────
    field_history = []
    try:
        history_rows = (
            db.query(FieldUpdateHistory)
            .filter(FieldUpdateHistory.case_id == case.case_id)
            .order_by(FieldUpdateHistory.changed_at.asc())
            .all()
        )
        for h in history_rows:
            field_history.append({
                "field_name": h.field_name,
                "old_value": h.old_value,
                "new_value": h.new_value,
                "source": h.source,
                "changed_by": h.changed_by,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
            })
    except Exception:
        pass

    # ── No-Response Tracking ─────────────────────────────────
    no_response = None
    try:
        pending_attempts = (
            db.query(FollowUpAttempt)
            .filter(
                FollowUpAttempt.case_id == case.case_id,
                FollowUpAttempt.status.in_(["PENDING", "SENT", "AWAITING_RESPONSE"]),
            )
            .order_by(FollowUpAttempt.sent_at.desc())
            .all()
        )
        if pending_attempts:
            last_sent = pending_attempts[0].sent_at
            days_since = (datetime.utcnow() - last_sent).days if last_sent else None
            nr_missing = set()
            for pa in pending_attempts:
                if pa.response_data and isinstance(pa.response_data, dict):
                    for q in pa.response_data.get("questions", []):
                        f = q.get("field") or q.get("field_name")
                        if f:
                            nr_missing.add(f)
            # Subtract fields already answered
            answered = {r.field_name for r in all_responses if r.field_value} if all_responses else set()
            nr_still = nr_missing - answered
            no_response = {
                "pending_count": len(pending_attempts),
                "last_attempt_date": last_sent.isoformat() if last_sent else None,
                "days_since_last_attempt": days_since,
                "still_missing_fields": list(nr_still),
            }
    except Exception:
        pass

    return {
        "case_summary": summary,
        "followup_timeline": followup_timeline,
        "clinical_narrative": narrative,
        "ml_risk": ml_risk,
        "regulatory_seriousness": regulatory,
        "lifecycle": lifecycle_status,
        "combined_package": combined_package,
        "attachments": attachments,
        "reporter_responses": reporter_responses,
        "field_history": field_history,
        "no_response": no_response,
        "review_status": {
            "human_reviewed": case.human_reviewed,
            "reviewed_by": case.reviewed_by,
            "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
            "review_notes": case.review_notes,
        },
        "package_built": _built_packages.get(str(case.case_id)) is not None,
        "built_package": _built_packages.get(str(case.case_id), {}).get("questions") if _built_packages.get(str(case.case_id)) else None,
    }


@router.post("/{case_id}/decision", response_model=ReviewerDecisionResponse)
async def submit_reviewer_decision(
    case_id: str,
    body: ReviewerDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Submit reviewer decision for a case.

    Allowed decisions:
    - APPROVE: Case review complete, approved by reviewer
    - REQUEST_MORE_INFO: Reviewer wants additional follow-up
    - ESCALATE: Escalate to senior medical reviewer / safety committee
    - CLOSE: Close case (no further action needed)

    This does NOT modify ML logic or override orchestration.
    """
    VALID_DECISIONS = {"APPROVE", "REQUEST_MORE_INFO", "ESCALATE", "CLOSE"}
    if body.decision.upper() not in VALID_DECISIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{body.decision}'. Must be one of: {VALID_DECISIONS}",
        )

    case = _find_case(case_id, db)
    previous_status = case.case_status
    decision = body.decision.upper()

    # Apply decision
    if decision == "APPROVE":
        case.case_status = "REVIEWER_APPROVED"
        case.human_reviewed = True
    elif decision == "REQUEST_MORE_INFO":
        case.case_status = "PENDING_FOLLOWUP"
        case.requires_followup = True
    elif decision == "ESCALATE":
        case.case_status = "ESCALATED"
    elif decision == "CLOSE":
        case.case_status = "CLOSED"
        case.requires_followup = False

    # Record review metadata
    case.reviewed_by = current_user.username if current_user else "unknown"
    case.reviewed_at = datetime.utcnow()
    if body.reviewer_comment:
        # Append to existing notes rather than overwrite
        existing = case.review_notes or ""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        new_note = f"[{timestamp}] {decision}: {body.reviewer_comment}"
        case.review_notes = f"{existing}\n{new_note}".strip() if existing else new_note

    case.updated_at = datetime.utcnow()

    # Audit log
    try:
        AuditService.log_activity(
            db=db,
            case_id=case.case_id,
            activity_type="REVIEWER_DECISION",
            description=f"Reviewer decision: {decision}. Comment: {body.reviewer_comment or 'N/A'}",
            user_id=str(current_user.user_id) if current_user else None,
        )
    except Exception as audit_err:
        logger.warning(f"Audit log failed (non-blocking): {audit_err}")

    db.commit()
    db.refresh(case)

    logger.info(
        f"Reviewer decision for case {case_id}: {decision} "
        f"(was: {previous_status} → now: {case.case_status}) "
        f"by {case.reviewed_by}"
    )

    return ReviewerDecisionResponse(
        success=True,
        case_id=str(case.case_id),
        decision=decision,
        previous_status=previous_status,
        new_status=case.case_status,
        reviewer=case.reviewed_by,
        timestamp=case.reviewed_at.isoformat(),
        message=f"Case {decision.lower().replace('_', ' ')} by reviewer.",
    )


# ── Follow-Up: 3-Step Flow ───────────────────────────────────
# Step 1: Save reviewer override questions (no send)
# Step 2: Build combined follow-up package (no send)
# Step 3: Send combined follow-up (only after build)
# ─────────────────────────────────────────────────────────────

# In-memory store for built combined packages (keyed by case_id string).
# Populated by build-combined, consumed by send-combined.
# Cleared after successful send.
_built_packages: dict = {}


class SaveOverrideRequest(BaseModel):
    reviewer_notes: Optional[List[str]] = None     # New: free-text reviewer notes
    reviewer_questions: Optional[List[str]] = None  # Legacy: backward compat


class SendFollowUpRequest(BaseModel):
    reviewer_questions: Optional[List[str]] = None  # Extra questions added by reviewer


# ── Step 1: Save Override Questions ──────────────────────────

@router.post("/{case_id}/save-override")
async def save_override_questions(
    case_id: str,
    body: SaveOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Save reviewer notes (or legacy override questions) for a case.

    This does NOT trigger any communication.
    Notes are stored on the case (review_notes) and will be converted
    to proper follow-up questions by AI when building the combined package.
    """
    case = _find_case(case_id, db)

    # Accept notes (new) or questions (legacy backward compat)
    items = body.reviewer_notes or body.reviewer_questions or []
    items = [item for item in items if item.strip()]

    if not items:
        return {
            "success": True,
            "case_id": str(case.case_id),
            "notes_saved": 0,
            "message": "No notes to save.",
        }

    # Store as REVIEWER_NOTE (new format) for AI conversion during build
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    note_block = f"[{timestamp}] REVIEWER_NOTE:\n" + "\n".join(
        f"  - {item}" for item in items
    )

    existing = case.review_notes or ""
    case.review_notes = f"{existing}\n{note_block}".strip() if existing else note_block
    case.updated_at = datetime.utcnow()
    db.commit()

    # Clear any previously built package (notes changed)
    cid = str(case.case_id)
    _built_packages.pop(cid, None)

    # Audit
    try:
        AuditService.log_activity(
            db=db,
            case_id=case.case_id,
            activity_type="REVIEWER_NOTES_SAVED",
            description=f"Reviewer saved {len(items)} notes for AI conversion.",
            user_id=str(current_user.user_id) if current_user else None,
        )
    except Exception:
        pass

    return {
        "success": True,
        "case_id": str(case.case_id),
        "notes_saved": len(items),
        "message": f"{len(items)} note(s) saved. Click 'Build Combined Follow-Up' — AI will convert these into proper questions.",
    }


# ── Step 2: Build Combined Follow-Up ────────────────────────

@router.post("/{case_id}/build-combined")
async def build_combined_package(
    case_id: str,
    body: Optional[SendFollowUpRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Build the combined follow-up package WITHOUT sending.

    Aggregates:
    - AI-generated missing-field questions
    - Reviewer override questions (inline from body)
    - Uploaded document attachments

    Stores the built package in memory so the send step can use it.
    No email / phone / WhatsApp is triggered here.
    """
    case = _find_case(case_id, db)

    from app.services.combined_followup import build_combined_followup
    combined = build_combined_followup(case, db)

    # Merge all questions into one flat list
    all_questions = []

    # 1. AI-generated missing field questions
    for q in combined.get("missing_questions", []):
        all_questions.append({
            "field": q.get("field_name") or q.get("field"),
            "field_name": q.get("field_name") or q.get("field"),
            "question_text": q.get("question") or q.get("question_text", ""),
            "criticality": q.get("criticality", "CRITICAL") if q.get("is_required") else "MEDIUM",
            "source": "AI",
        })

    # 2. Reviewer-added manual questions (from documents)
    for q in combined.get("reviewer_questions", []):
        all_questions.append({
            "field": q.get("field_name") or q.get("field", "reviewer_custom"),
            "field_name": q.get("field_name") or q.get("field", "reviewer_custom"),
            "question_text": q.get("question") or q.get("question_text", ""),
            "criticality": "HIGH",
            "source": "REVIEWER",
        })

    # 3. Convert reviewer notes to AI-generated questions
    #    Extract saved notes from case.review_notes (REVIEWER_NOTE blocks)
    #    and convert them to proper PV questions using Mistral LLM.
    reviewer_notes_raw = []
    if case.review_notes:
        for line in case.review_notes.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                reviewer_notes_raw.append(stripped[2:].strip())

    # Also accept inline notes from request body (backward compat)
    if body and body.reviewer_questions:
        for q_text in body.reviewer_questions:
            if q_text.strip() and q_text.strip() not in reviewer_notes_raw:
                reviewer_notes_raw.append(q_text.strip())

    logger.info(f"build-combined: {len(reviewer_notes_raw)} reviewer notes found for AI conversion")

    if reviewer_notes_raw:
        try:
            from app.services.combined_followup import convert_reviewer_notes_to_questions
            case_data = {
                "suspect_drug": case.suspect_drug,
                "adverse_event": case.adverse_event,
                "reporter_type": case.reporter_type,
                "patient_age": case.patient_age,
                "patient_sex": case.patient_sex,
                "event_outcome": case.event_outcome,
                "is_serious": case.is_serious,
            }
            ai_converted = convert_reviewer_notes_to_questions(
                notes=reviewer_notes_raw,
                case_data=case_data,
                existing_questions=all_questions,
            )

            # SAFETY NET: if AI conversion returned 0 items, use raw notes directly
            if not ai_converted:
                logger.warning("build-combined: AI conversion returned 0 items — using raw notes as questions")
                ai_converted = []
                for i, note in enumerate(reviewer_notes_raw):
                    ai_converted.append({
                        "field_name": f"reviewer_note_{i+1}",
                        "question": note,
                        "question_text": note,
                        "criticality": "HIGH",
                        "source": "REVIEWER_NOTE_RAW",
                        "original_note": note,
                    })

            for q in ai_converted:
                q_text = q.get("question_text") or q.get("question", "")
                already_exists = q_text in {aq.get("question_text", "") for aq in all_questions}
                if not already_exists:
                    all_questions.append({
                        "field": q.get("field_name", "reviewer_custom"),
                        "field_name": q.get("field_name", "reviewer_custom"),
                        "question_text": q_text,
                        "question": q_text,
                        "criticality": q.get("criticality", "HIGH"),
                        "source": q.get("source", "REVIEWER_NOTE_AI"),
                        "original_note": q.get("original_note", ""),
                    })
            logger.info(f"build-combined: AI converted {len(ai_converted)} notes into questions")
        except Exception as conv_err:
            logger.error(f"build-combined: Reviewer note conversion FAILED: {conv_err}", exc_info=True)
            # FALLBACK: Add raw notes directly as questions
            for i, note in enumerate(reviewer_notes_raw):
                all_questions.append({
                    "field": f"reviewer_note_{i+1}",
                    "field_name": f"reviewer_note_{i+1}",
                    "question_text": note,
                    "question": note,
                    "criticality": "HIGH",
                    "source": "REVIEWER_NOTE_RAW",
                    "original_note": note,
                })
            logger.info(f"build-combined: FALLBACK added {len(reviewer_notes_raw)} raw notes as questions")

    logger.info(f"build-combined total: {len(all_questions)} questions ({len([q for q in all_questions if q['source'] == 'AI'])} AI + {len([q for q in all_questions if q['source'] != 'AI'])} reviewer/notes)")

    if not all_questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Combined package is empty — no questions to send. Upload documents or analyze the case first.",
        )

    # ── REORDER: Put REVIEWER/REPO questions FIRST so they're asked ──
    # before AI questions can push completeness to 100% and trigger early termination
    priority_qs = []
    regular_qs = []
    for q in all_questions:
        src = (q.get("source") or "").upper()
        if "REVIEWER" in src or "REPO" in src or "CHECKLIST" in src:
            priority_qs.append(q)
        else:
            regular_qs.append(q)
    if priority_qs:
        all_questions = priority_qs + regular_qs
        logger.info(f"🔀 Reordered: {len(priority_qs)} reviewer/repo Qs moved to front, {len(regular_qs)} AI Qs after")

    # Store built package
    cid = str(case.case_id)
    _built_packages[cid] = {
        "questions": all_questions,
        "attachments": combined.get("attachments", []),
        "combined_raw": combined,
        "built_at": datetime.utcnow().isoformat(),
        "built_by": current_user.username if current_user else "unknown",
    }

    # Audit
    try:
        AuditService.log_activity(
            db=db,
            case_id=case.case_id,
            activity_type="COMBINED_PACKAGE_BUILT",
            description=f"Combined follow-up package built: {len(all_questions)} questions, {len(combined.get('attachments', []))} attachments.",
            user_id=str(current_user.user_id) if current_user else None,
        )
    except Exception:
        pass

    return {
        "success": True,
        "case_id": cid,
        "questions": all_questions,
        "attachments": combined.get("attachments", []),
        "total_questions": len(all_questions),
        "ai_questions": len([q for q in all_questions if q["source"] == "AI"]),
        "reviewer_questions": len([q for q in all_questions if q["source"] in ("REVIEWER", "REVIEWER_INLINE", "REVIEWER_OVERRIDE", "REVIEWER_NOTE_AI", "REVIEWER_NOTE_RAW")]),
        "note_converted_questions": len([q for q in all_questions if q["source"] in ("REVIEWER_NOTE_AI", "REVIEWER_NOTE_RAW")]),
        "message": f"Combined package built with {len(all_questions)} questions. Ready to send.",
        "ready_to_send": True,
    }


# ── Step 3: Send Combined Follow-Up ─────────────────────────

@router.post("/{case_id}/send-followup")
async def send_followup_manually(
    case_id: str,
    body: Optional[SendFollowUpRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Send the combined follow-up package via ALL channels (EMAIL, PHONE, WHATSAPP).

    REQUIRES: The combined package must be built first via POST /{case_id}/build-combined.
    If no built package exists, this endpoint returns 409 Conflict.

    This is the ONLY place where actual communication (Twilio, SMTP) is triggered.
    """
    case = _find_case(case_id, db)
    cid = str(case.case_id)

    # ── Guard: package must be built first ──
    built = _built_packages.get(cid)
    if not built:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Combined follow-up package has not been built yet. Click 'Build Combined Follow-Up' first.",
        )

    all_questions = built["questions"]
    attachments = built["attachments"]

    # Build analysis_result dict for the trigger
    analysis_result = {
        "followup_required": True,
        "decision": "PROCEED",
        "risk_score": case.seriousness_score or 0.0,
        "completeness_score": case.data_completeness_score or 0.0,
        "response_probability": 0.5,
        "stop_followup": False,
        "followup_channel": "MULTI",
    }

    # Include attachments in the analysis result
    if attachments:
        analysis_result["followup_attachments"] = attachments

    # Send via multi-channel trigger
    from app.services.followup_trigger import FollowUpTrigger

    followup_result = await FollowUpTrigger.trigger_automated_followup(
        db=db,
        case=case,
        analysis_result=analysis_result,
        questions=all_questions,
        user_id=str(current_user.user_id) if current_user else None,
    )

    # Update lifecycle if follow-up was created
    if followup_result.get("followup_created"):
        try:
            from app.services.lifecycle_db_service import LifecycleDBService
            lifecycle_service = LifecycleDBService(db)
            lifecycle = lifecycle_service.get_lifecycle_by_case_id(str(case.case_id))
            if lifecycle:
                lifecycle = lifecycle_service.record_followup_sent(
                    lifecycle=lifecycle,
                    questions_sent=all_questions,
                    channel=followup_result.get("channel", "MULTI"),
                    sent_to=followup_result.get("contact_info", {}).get("email") if followup_result.get("contact_info") else None,
                )
                logger.info(f"Lifecycle updated: follow-up #{lifecycle.attempt_count} for case {case.case_id}")
        except Exception as lc_err:
            logger.warning(f"Lifecycle update failed (non-blocking): {lc_err}")

    # Audit log
    try:
        AuditService.log_activity(
            db=db,
            case_id=case.case_id,
            activity_type="COMBINED_FOLLOWUP_SENT",
            description=f"Combined follow-up sent by reviewer. {len(all_questions)} questions via {followup_result.get('channel', 'MULTI')}",
            user_id=str(current_user.user_id) if current_user else None,
        )
    except Exception:
        pass

    # Clear the built package after successful send
    _built_packages.pop(cid, None)

    return {
        "success": followup_result.get("followup_created", False),
        "case_id": cid,
        "primaryid": case.primaryid,
        "questions_sent": len(all_questions),
        "channels": followup_result.get("channels", []),
        "successful_channels": followup_result.get("successful_channels", []),
        "failed_channels": followup_result.get("failed_channels", []),
        "decision_id": followup_result.get("decision_id"),
        "questions": all_questions,
        "attachments": attachments,
        "message": followup_result.get("message", "Follow-up triggered"),
    }


# ── Reporter Responses Viewer ────────────────────────────────

@router.get("/{case_id}/responses")
async def get_case_responses(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all reporter responses for a case.

    Returns responses grouped by attempt, with answered/pending/missing breakdown.
    Includes full question text, raw response text, channel, version history.
    """
    case = _find_case(case_id, db)

    attempts = (
        db.query(FollowUpAttempt)
        .filter(FollowUpAttempt.case_id == case.case_id)
        .order_by(FollowUpAttempt.created_at.asc())
        .all()
    )

    attempt_responses = []
    total_answered = 0
    total_pending = 0

    for a in attempts:
        responses = (
            db.query(FollowUpResponse)
            .filter(FollowUpResponse.attempt_id == a.attempt_id)
            .order_by(FollowUpResponse.responded_at.asc())
            .all()
        )

        questions_sent = []
        if a.response_data and isinstance(a.response_data, dict):
            questions_sent = a.response_data.get("questions", [])

        answered_fields = {r.field_name for r in responses if r.field_value}
        question_fields = {q.get("field") or q.get("field_name") for q in questions_sent}
        pending_fields = question_fields - answered_fields

        total_answered += len(answered_fields)
        total_pending += len(pending_fields)

        attempt_responses.append({
            "attempt_id": str(a.attempt_id),
            "channel": a.channel,
            "status": a.status,
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
            "responded_at": a.responded_at.isoformat() if a.responded_at else None,
            "questions_sent": questions_sent,
            "responses": [
                {
                    "response_id": str(r.response_id),
                    "field_name": r.field_name,
                    "question_text": r.question_text,
                    "response_text": r.response_text,
                    "field_value": r.field_value,
                    "previous_value": r.previous_value,
                    "channel": r.channel,
                    "is_complete": r.is_complete,
                    "is_validated": r.is_validated,
                    "processed": r.processed,
                    "needs_clarification": r.needs_clarification,
                    "extraction_confidence": r.extraction_confidence,
                    "responded_at": r.responded_at.isoformat() if r.responded_at else None,
                }
                for r in responses
            ],
            "answered_fields": list(answered_fields),
            "pending_fields": list(pending_fields),
        })

    # Also get orphan responses (no attempt_id — e.g. direct web form)
    orphan_responses = (
        db.query(FollowUpResponse)
        .filter(
            FollowUpResponse.case_id == case.case_id,
            FollowUpResponse.attempt_id.is_(None),
        )
        .order_by(FollowUpResponse.responded_at.asc())
        .all()
    )
    if orphan_responses:
        attempt_responses.append({
            "attempt_id": None,
            "channel": "DIRECT",
            "status": "RESPONDED",
            "sent_at": None,
            "responded_at": orphan_responses[-1].responded_at.isoformat() if orphan_responses[-1].responded_at else None,
            "questions_sent": [],
            "responses": [
                {
                    "response_id": str(r.response_id),
                    "field_name": r.field_name,
                    "question_text": r.question_text,
                    "response_text": r.response_text,
                    "field_value": r.field_value,
                    "previous_value": r.previous_value,
                    "channel": r.channel,
                    "is_complete": r.is_complete,
                    "is_validated": r.is_validated,
                    "processed": r.processed,
                    "needs_clarification": r.needs_clarification,
                    "extraction_confidence": r.extraction_confidence,
                    "responded_at": r.responded_at.isoformat() if r.responded_at else None,
                }
                for r in orphan_responses
            ],
            "answered_fields": list({r.field_name for r in orphan_responses if r.field_value}),
            "pending_fields": [],
        })

    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "total_attempts": len(attempts),
        "total_answered": total_answered,
        "total_pending": total_pending,
        "attempts": attempt_responses,
    }


# ── Field Update History ────────────────────────────────────

@router.get("/{case_id}/field-history")
async def get_field_update_history(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the version history for all case fields changed by reporter responses.

    Returns every old→new change with source, timestamp, and linked response_id.
    """
    case = _find_case(case_id, db)

    history = (
        db.query(FieldUpdateHistory)
        .filter(FieldUpdateHistory.case_id == case.case_id)
        .order_by(FieldUpdateHistory.changed_at.asc())
        .all()
    )

    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "total_changes": len(history),
        "changes": [
            {
                "id": str(h.id),
                "field_name": h.field_name,
                "old_value": h.old_value,
                "new_value": h.new_value,
                "source": h.source,
                "changed_by": h.changed_by,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
                "response_id": str(h.response_id) if h.response_id else None,
            }
            for h in history
        ],
    }


# ── No-Response Tracking ────────────────────────────────────

@router.get("/{case_id}/no-response")
async def get_no_response_tracking(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Track follow-up attempts that have NOT received any response.

    Returns: pending attempts, last attempt date, days since last attempt,
    unanswered fields still missing.
    """
    case = _find_case(case_id, db)

    pending_attempts = (
        db.query(FollowUpAttempt)
        .filter(
            FollowUpAttempt.case_id == case.case_id,
            FollowUpAttempt.status.in_(["PENDING", "SENT", "AWAITING_RESPONSE"]),
        )
        .order_by(FollowUpAttempt.sent_at.desc())
        .all()
    )

    expired_attempts = (
        db.query(FollowUpAttempt)
        .filter(
            FollowUpAttempt.case_id == case.case_id,
            FollowUpAttempt.status.in_(["EXPIRED", "NO_RESPONSE"]),
        )
        .order_by(FollowUpAttempt.sent_at.desc())
        .all()
    )

    last_sent = None
    days_since = None
    if pending_attempts:
        last_sent = pending_attempts[0].sent_at
    elif expired_attempts:
        last_sent = expired_attempts[0].sent_at

    if last_sent:
        days_since = (datetime.utcnow() - last_sent).days

    # Collect all fields still awaiting response
    all_requested = set()
    all_answered = set()
    for a in pending_attempts + expired_attempts:
        if a.response_data and isinstance(a.response_data, dict):
            for q in a.response_data.get("questions", []):
                f = q.get("field") or q.get("field_name")
                if f:
                    all_requested.add(f)
        resps = (
            db.query(FollowUpResponse)
            .filter(FollowUpResponse.attempt_id == a.attempt_id, FollowUpResponse.field_value.isnot(None))
            .all()
        )
        for r in resps:
            all_answered.add(r.field_name)
    still_missing = list(all_requested - all_answered)

    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "pending_count": len(pending_attempts),
        "expired_count": len(expired_attempts),
        "last_attempt_date": last_sent.isoformat() if last_sent else None,
        "days_since_last_attempt": days_since,
        "still_missing_fields": still_missing,
        "pending_attempts": [
            {
                "attempt_id": str(a.attempt_id),
                "channel": a.channel,
                "sent_at": a.sent_at.isoformat() if a.sent_at else None,
                "sent_to": a.sent_to,
                "questions_count": a.questions_count or 0,
                "status": a.status,
            }
            for a in pending_attempts
        ],
        "expired_attempts": [
            {
                "attempt_id": str(a.attempt_id),
                "channel": a.channel,
                "sent_at": a.sent_at.isoformat() if a.sent_at else None,
                "status": a.status,
            }
            for a in expired_attempts
        ],
    }
