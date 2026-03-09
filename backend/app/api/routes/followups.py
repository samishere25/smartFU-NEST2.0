"""
Follow-Up Management Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.models.followup import FollowUpDecision, FollowUpAttempt
from app.schemas.followup import FollowUpDecision as FollowUpDecisionSchema
from app.core.security import get_current_active_user

router = APIRouter()


# ================================================================
# Micro-Question Flow Endpoints (must be before /{case_id} routes)
# ================================================================

# Question type mapping for UI rendering
FIELD_QUESTION_TYPES = {
    "patient_sex": {
        "question_type": "select",
        "options": ["Male", "Female", "Unknown"]
    },
    "event_date": {"question_type": "date"},
    "receipt_date": {"question_type": "date"},
    "patient_age": {"question_type": "number"},
    "is_serious": {"question_type": "boolean"},
    "event_outcome": {
        "question_type": "select",
        "options": [
            "Recovered/Resolved",
            "Recovering/Resolving",
            "Not Recovered/Not Resolved",
            "Recovered with Sequelae",
            "Fatal",
            "Unknown"
        ]
    },
    "drug_route": {
        "question_type": "select",
        "options": ["Oral", "Intravenous", "Intramuscular", "Subcutaneous", "Topical", "Inhalation", "Other"]
    },
    "reporter_type": {
        "question_type": "select",
        "options": ["Physician (MD)", "Pharmacist (PH)", "Nurse (HP)", "Consumer (CN)", "Patient (PT)", "Lawyer (LW)", "Other (OT)"]
    },
}


def _find_case(db, case_id_str: str):
    """Helper to find a case by primaryid or UUID."""
    from app.models.case import AECase
    try:
        case = db.query(AECase).filter(AECase.primaryid == int(case_id_str)).first()
    except (ValueError, TypeError):
        try:
            case = db.query(AECase).filter(AECase.case_id == UUID(case_id_str)).first()
        except Exception:
            case = None
    return case


@router.get("/next-question")
async def get_next_question(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the single highest-priority next question for a case.
    Used by the interactive micro-question flow.
    """
    from app.services.data_completeness import DataCompletenessService
    from app.services.question_scoring import QuestionValueScorer

    case = _find_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Build case data dict for completeness analysis
    case_data = {
        "patient_age": case.patient_age,
        "patient_sex": case.patient_sex,
        "event_date": case.event_date,
        "event_outcome": case.event_outcome,
        "adverse_event": case.adverse_event,
        "suspect_drug": case.suspect_drug,
        "drug_dose": case.drug_dose,
        "drug_route": case.drug_route,
        "reporter_type": case.reporter_type,
        "reporter_country": case.reporter_country,
        "receipt_date": case.receipt_date,
    }

    # Analyze completeness
    analysis = DataCompletenessService.analyze_case(case_data)
    completeness_score = analysis["completeness_score"]
    missing_fields = analysis["missing_fields"]
    critical_missing_count = analysis["critical_missing_count"]

    # Check stop conditions
    if completeness_score >= 0.85 or not missing_fields:
        return {
            "next_question": None,
            "completeness_score": completeness_score,
            "is_complete": True
        }

    risk_score = case.seriousness_score or 0.0

    # Use Feature-3 enhanced scoring to pick the top question
    result = QuestionValueScorer.generate_adaptive_questions(
        missing_fields=missing_fields,
        risk_score=risk_score,
        completeness_score=completeness_score,
        decision="PROCEED",
        critical_missing_count=critical_missing_count,
        max_questions=1
    )

    if result["stop_followup"] or not result["questions"]:
        return {
            "next_question": None,
            "completeness_score": completeness_score,
            "is_complete": True
        }

    top_question = result["questions"][0]
    field_name = top_question["field"]

    # Determine question_type and options for UI rendering
    type_info = FIELD_QUESTION_TYPES.get(field_name, {"question_type": "text"})

    return {
        "next_question": {
            "field_name": field_name,
            "question_text": top_question["question"],
            "question_type": type_info["question_type"],
            "options": type_info.get("options"),
            "criticality": top_question["criticality"],
            "why_it_matters": top_question.get("safety_impact", ""),
            "value_score": top_question.get("value_score", 0.0),
        },
        "completeness_score": completeness_score,
        "is_complete": False,
        "followup_priority": "CRITICAL" if critical_missing_count > 0 else "HIGH"
    }


from pydantic import BaseModel
from typing import Any, Optional


class FollowUpAnswerRequest(BaseModel):
    case_id: str
    field_name: str
    answer: Any


@router.post("/answer")
async def submit_followup_answer(
    payload: FollowUpAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit a single follow-up answer and return updated completeness.
    Used by the interactive micro-question flow.
    """
    from app.models.case import AECase, MissingField
    from app.services.data_completeness import DataCompletenessService
    from app.services.question_scoring import QuestionValueScorer
    from datetime import datetime

    case = _find_case(db, payload.case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    field_name = payload.field_name
    answer = payload.answer

    # Map of field_name -> AECase column for direct update
    field_column_map = {
        "patient_age": "patient_age",
        "patient_sex": "patient_sex",
        "event_date": "event_date",
        "event_outcome": "event_outcome",
        "adverse_event": "adverse_event",
        "suspect_drug": "suspect_drug",
        "drug_dose": "drug_dose",
        "drug_route": "drug_route",
        "reporter_type": "reporter_type",
        "reporter_country": "reporter_country",
        "receipt_date": "receipt_date",
    }

    # Update the case field if it maps to a column
    if field_name in field_column_map:
        col = field_column_map[field_name]
        # Type coercion for specific fields
        if field_name == "patient_age":
            try:
                answer = int(answer)
            except (ValueError, TypeError):
                pass
        elif field_name in ("event_date", "receipt_date"):
            try:
                answer = datetime.fromisoformat(str(answer))
            except (ValueError, TypeError):
                pass
        setattr(case, col, answer)

    # Mark the missing field as no longer missing
    missing = db.query(MissingField).filter(
        MissingField.case_id == case.case_id,
        MissingField.field_name == field_name
    ).first()
    if missing:
        missing.is_missing = False

    # Recalculate completeness
    case_data = {
        "patient_age": case.patient_age,
        "patient_sex": case.patient_sex,
        "event_date": case.event_date,
        "event_outcome": case.event_outcome,
        "adverse_event": case.adverse_event,
        "suspect_drug": case.suspect_drug,
        "drug_dose": case.drug_dose,
        "drug_route": case.drug_route,
        "reporter_type": case.reporter_type,
        "reporter_country": case.reporter_country,
        "receipt_date": case.receipt_date,
    }
    analysis = DataCompletenessService.analyze_case(case_data)
    new_completeness = analysis["completeness_score"]

    # Update case completeness and status
    old_completeness = case.data_completeness_score or 0.0
    case.data_completeness_score = new_completeness
    case.updated_at = datetime.utcnow()

    is_complete = new_completeness >= 0.85 or analysis["critical_missing_count"] == 0

    if is_complete:
        case.case_status = "FOLLOWUP_RECEIVED"

    db.commit()

    # Update RL feedback
    try:
        QuestionValueScorer.update_rl_feedback(
            field_name=field_name,
            answered=True,
            completeness_increase=new_completeness - old_completeness,
            is_critical=(missing.safety_criticality == "CRITICAL") if missing else False
        )
    except Exception:
        pass  # Non-critical

    # Auto-update lifecycle tracker on response
    try:
        from app.services.lifecycle_db_service import LifecycleDBService
        lifecycle_service = LifecycleDBService(db)
        lifecycle = lifecycle_service.get_lifecycle_by_case_id(str(case.case_id))
        if lifecycle:
            lifecycle = lifecycle_service.record_response_received(
                lifecycle=lifecycle,
                questions_answered=1,
                completeness_score=new_completeness,
                safety_confidence=new_completeness,
                is_complete=is_complete
            )
            if lifecycle.response_status == "complete":
                lifecycle_service.close_case_success(lifecycle)
    except Exception:
        pass  # Non-critical - don't fail the answer submission

    return {
        "status": "success",
        "field_name": field_name,
        "completeness_score": new_completeness,
        "is_complete": is_complete,
        "completeness_increase": round(new_completeness - old_completeness, 3)
    }


@router.post("/{case_id}/decide", response_model=FollowUpDecisionSchema)
async def decide_followup(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger follow-up decision for a case"""
    
    # Import agent
    from app.agents.graph import smartfu_agent, SmartFUState
    from app.models.case import AECase
    
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Run agent workflow
    initial_state = SmartFUState(
        case_id=str(case_id),
        case_data={
            "suspect_drug": case.suspect_drug,
            "adverse_event": case.adverse_event,
            "reporter_type": case.reporter_type
        },
        missing_fields=[{"field_name": mf.field_name} for mf in case.missing_fields],
        risk_score=case.seriousness_score,
        response_probability=0.0,
        decision="PENDING",
        questions=[],
        reasoning="",
        messages=[]
    )
    
    result = await smartfu_agent.ainvoke(initial_state)
    
    # Save decision
    decision = FollowUpDecision(
        case_id=case_id,
        decision_type=result["decision"],
        decision_reason=result["reasoning"],
        confidence_score=0.85,
        predicted_response_probability=result["response_probability"],
        case_risk_level="HIGH" if result["risk_score"] > 0.7 else "MEDIUM"
    )
    
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    return decision

@router.get("/{case_id}", response_model=List[FollowUpDecisionSchema])
async def get_followup_history(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get follow-up history for a case"""
    
    decisions = db.query(FollowUpDecision).filter(
        FollowUpDecision.case_id == case_id
    ).order_by(FollowUpDecision.created_at.desc()).all()
    
    return decisions


@router.get("/{case_id}/questions")
async def get_followup_questions(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get follow-up questions for a case - Feature 4 endpoint"""
    from app.models.case import AECase
    
    # Try to find case by primaryid first, then by UUID
    try:
        # Try as primaryid (integer)
        case = db.query(AECase).filter(AECase.primaryid == int(case_id)).first()
    except ValueError:
        # Try as UUID
        try:
            case = db.query(AECase).filter(AECase.case_id == UUID(case_id)).first()
        except:
            case = None
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Get latest PENDING follow-up attempt for this case (Feature 4 data)
    # Use raw SQL to avoid PostgreSQL type 25 error with status column
    from sqlalchemy import text
    
    sql = text("""
        SELECT attempt_id, case_id, questions_sent, channel, reasoning, questions_count, created_at
        FROM followup_attempts 
        WHERE case_id = :case_id 
        AND status::text = 'PENDING'
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    result = db.execute(sql, {"case_id": str(case.case_id)}).first()
    
    # Create a simple object to hold the data
    followup = None
    if result:
        class FollowupData:
            def __init__(self, row):
                self.attempt_id = row[0]
                self.case_id = row[1]
                self.questions_sent = row[2]
                self.channel = row[3]
                self.reasoning = row[4]
                self.questions_count = row[5]
                self.created_at = row[6]
                self.status = "PENDING"  # We know it's PENDING from the query
        
        followup = FollowupData(result)
    
    # If follow-up exists with questions, use those (from Feature 3 + 4)
    if followup and followup.questions_sent:
        questions_data = followup.questions_sent
        
        # Format questions for frontend
        questions = []
        for q in questions_data:
            question = {
                "question_id": f"q_{q.get('field_name', 'unknown')}",
                "question_text": q.get('question', f"What is the {q.get('field_name', 'information')}?"),
                "field_type": q.get('field_name', 'unknown'),
                "criticality": q.get('criticality', 'MEDIUM'),
                "why_it_matters": q.get('safety_impact', 'This information is important for safety assessment.'),
                "input_type": "date" if "date" in q.get('field_name', '').lower() else "text",
                "value_score": q.get('value_score'),
                "options": ["Male", "Female", "Unknown"] if "sex" in q.get('field_name', '').lower() else None
            }
            questions.append(question)
        
        return {
            "case_id": str(case.case_id),
            "primaryid": case.primaryid,
            "followup_id": str(followup.attempt_id),
            "channel": followup.channel or "EMAIL",
            "priority": "CRITICAL" if any(q.get('criticality') == 'CRITICAL' for q in questions_data) else "HIGH",
            "purpose": "This follow-up is requested based on automated safety assessment to collect critical missing information.",
            "expiry_hours": 72,
            "explanation": {
                "missing_safety_fields": f"This case has {len(questions)} critical or high-priority missing fields.",
                "safety_impact": "Missing critical data may affect our ability to assess the safety signal and take appropriate action.",
                "regulatory_context": "Regulatory agencies require complete adverse event reports for proper safety monitoring.",
                "adaptive_decision": f"AI question scoring selected {len(questions)} high-value questions from {followup.questions_count or len(questions)} missing fields."
            },
            "questions": questions,
            "reasoning": followup.reasoning or "Additional information needed for complete safety assessment",
            "orchestration": {
                "channel": followup.channel,
                "timing_hours": 0,  # Already sent
                "questions_count": len(questions),
                "status": followup.status
            }
        }
    
    # Fallback: If no follow-up stored, build from missing fields (backward compatibility)
    questions = []
    for mf in case.missing_fields:
        question = {
            "question_id": f"q_{mf.field_name}",
            "question_text": f"What is the {mf.field_name.replace('_', ' ')}?",
            "field_type": mf.field_name,
            "criticality": mf.safety_criticality or "MEDIUM",
            "why_it_matters": f"This information is critical for safety assessment and regulatory compliance.",
            "input_type": "date" if "date" in mf.field_name.lower() else "text",
            "options": ["Male", "Female", "Unknown"] if "sex" in mf.field_name.lower() else None
        }
        questions.append(question)
    
    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "purpose": "This follow-up is requested only for patient safety and regulatory compliance.",
        "expiry_hours": 72,
        "explanation": {
            "missing_safety_fields": f"This case requires additional information to complete the safety evaluation.",
            "safety_impact": "Missing critical data may affect our ability to assess the safety signal and take appropriate action.",
            "regulatory_context": "Regulatory agencies require complete adverse event reports for proper safety monitoring."
        },
        "questions": questions,
        "reasoning": "Additional information needed for complete safety assessment"
    }


@router.post("/{case_id}/submit")
async def submit_followup(
    case_id: str,
    responses: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit follow-up responses - Feature 4 endpoint"""
    from app.models.case import AECase
    
    # Try to find case
    try:
        case = db.query(AECase).filter(AECase.primaryid == int(case_id)).first()
    except ValueError:
        try:
            case = db.query(AECase).filter(AECase.case_id == UUID(case_id)).first()
        except:
            case = None
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Create follow-up attempt record
    attempt = FollowUpAttempt(
        case_id=case.case_id,
        response_status="RESPONDED",
        response_data=responses,
        channel="WEB_FORM"
    )
    
    db.add(attempt)
    
    # Update case status
    case.case_status = "FOLLOWUP_RECEIVED"
    
    # Get old status for audit
    old_status = "PENDING_FOLLOWUP"
    
    db.commit()
    
    # Feature 6: Re-evaluate signals after follow-up response
    from app.services.signal_service import evaluate_signals_for_case
    signal_result = await evaluate_signals_for_case(case, db)
    
    # Feature 7: Log case status change in audit trail
    from app.services.audit_service import AuditService
    AuditService.log_case_status_change(
        db=db,
        case_id=case.case_id,
        user_id=None,  # Reporter response, not user-initiated
        old_status=old_status,
        new_status="FOLLOWUP_RECEIVED",
        reason="Reporter submitted follow-up responses"
    )
    
    return {
        "status": "success",
        "message": "Follow-up response recorded successfully",
        "signals": signal_result
    }


@router.post("/{case_id}/decline")
async def decline_followup(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Decline follow-up - Feature 4 endpoint"""
    from app.models.case import AECase
    
    # Try to find case
    try:
        case = db.query(AECase).filter(AECase.primaryid == int(case_id)).first()
    except ValueError:
        try:
            case = db.query(AECase).filter(AECase.case_id == UUID(case_id)).first()
        except:
            case = None
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Create follow-up attempt record
    attempt = FollowUpAttempt(
        case_id=case.case_id,
        response_status="DECLINED",
        contact_method="WEB_FORM"
    )
    
    db.add(attempt)
    
    # Update case status
    case.case_status = "FOLLOWUP_DECLINED"
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Follow-up declined"
    }


@router.post("/{case_id}/override-questions")
async def submit_override_questions(
    case_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit reviewer-override questions and trigger follow-up email immediately.
    
    Accepts: { "questions": [{ "field": "...", "question": "...", "criticality": "...", "value_score": 0.9 }, ...] }
    """
    from app.models.case import AECase
    from app.services.followup_trigger import FollowUpTrigger
    import logging
    
    logger = logging.getLogger(__name__)
    
    questions = body.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="No questions provided")
    
    # Find the case
    case = None
    try:
        case = db.query(AECase).filter(AECase.primaryid == int(case_id)).first()
    except (ValueError, TypeError):
        pass
    if not case:
        try:
            case = db.query(AECase).filter(AECase.case_id == UUID(case_id)).first()
        except:
            pass
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Ensure each question has required fields with defaults
    formatted_questions = []
    for q in questions:
        formatted_questions.append({
            "field": q.get("field") or q.get("field_name", "custom"),
            "field_name": q.get("field") or q.get("field_name", "custom"),
            "question": q.get("question", ""),
            "criticality": q.get("criticality", "HIGH"),
            "value_score": q.get("value_score", 0.9),
            "reviewer_override": True,
        })
    
    logger.info(f"📝 Reviewer override: {len(formatted_questions)} questions for case {case.case_id}")

    # ── Merge with supplementary questions (reviewer notes + checklist) ──
    try:
        from app.services.combined_followup import get_supplementary_questions
        existing_fields = set(q["field"] for q in formatted_questions)
        supplementary = get_supplementary_questions(case, db, existing_fields=existing_fields)

        reviewer_qs = supplementary.get("reviewer_questions", [])
        checklist_qs = supplementary.get("checklist_questions", [])
        attachments = supplementary.get("attachments", [])

        if reviewer_qs:
            formatted_questions.extend(reviewer_qs)
            logger.info(f"   + {len(reviewer_qs)} reviewer-note questions merged")
        if checklist_qs:
            formatted_questions.extend(checklist_qs)
            logger.info(f"   + {len(checklist_qs)} checklist questions merged")
    except Exception as merge_err:
        logger.warning(f"⚠️ Could not merge supplementary questions: {merge_err}")
        attachments = []

    logger.info(f"📋 Total questions after merge: {len(formatted_questions)}")

    # Build minimal analysis_result for the trigger
    analysis_result = {
        "followup_required": True,
        "decision": "ASK",
        "risk_score": case.seriousness_score or 0.5,
        "completeness_score": case.data_completeness_score or 0.0,
        "questions": formatted_questions,
    }
    # Attach supplementary PDFs if any
    if attachments:
        analysis_result["followup_attachments"] = attachments

    # Trigger follow-up (sends email/phone/whatsapp)
    try:
        followup_result = await FollowUpTrigger.trigger_automated_followup(
            db=db,
            case=case,
            analysis_result=analysis_result,
            questions=formatted_questions,
            user_id=str(current_user.user_id) if current_user else None
        )

        logger.info(f"✅ Reviewer override follow-up sent for case {case.case_id}: {followup_result}")

        return {
            "status": "success",
            "message": f"Follow-up sent with {len(formatted_questions)} questions ({len(formatted_questions) - len(questions)} supplementary)",
            "followup": followup_result,
            "questions_count": len(formatted_questions),
        }
    except Exception as e:
        logger.error(f"❌ Reviewer override follow-up failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send follow-up: {str(e)}")


@router.get("/attempts/all")
async def get_all_followup_attempts(
    limit: int = 100,
    skip: int = 0,
    status: str = None,
    db: Session = Depends(get_db),
    _user = Depends(get_current_active_user)
):
    """Get all follow-up attempts for tracking with case details"""
    from app.models.case import AECase
    from datetime import datetime
    import logging
    
    # WORKAROUND: Due to PostgreSQL type 25 error with FollowUpAttempt table,
    # we'll show cases that have been analyzed and have follow-up data
    try:
        # Get cases that have seriousness_score > 0 (have been analyzed)
        query = db.query(AECase).filter(
            AECase.seriousness_score.isnot(None)
        )
        
        # Filter by completeness for status
        if status == "COMPLETE":
            # Show cases with high completeness (answered questions)
            query = query.filter(AECase.data_completeness_score >= 0.6)
        elif status == "PENDING":
            # Show cases with low completeness (pending questions)
            query = query.filter(AECase.data_completeness_score < 0.6)
        
        cases = query.order_by(AECase.updated_at.desc()).offset(skip).limit(limit).all()
        
        return {
            "attempts": [
                {
                    "attempt_id": str(case.case_id),  # Using case_id as attempt_id
                    "case_id": str(case.case_id),
                    "primaryid": case.primaryid,
                    "channel": "EMAIL",  # Default channel
                    "status": "COMPLETE" if case.data_completeness_score >= 0.6 else "AWAITING_RESPONSE",
                    "response_status": "RESPONDED" if case.data_completeness_score >= 0.6 else "PENDING",
                    "questions_count": 3,  # Fixed count based on fallback questions
                    "sent_at": case.updated_at.isoformat() if case.updated_at else None,
                    "responded_at": case.updated_at.isoformat() if case.data_completeness_score >= 0.6 else None,
                    "drug_name": case.suspect_drug,
                    "adverse_event": case.adverse_event,
                    "seriousness_score": case.seriousness_score or 0.0,
                    "completeness_score": case.data_completeness_score or 0.0,
                }
                for case in cases
            ],
            "total": len(cases)
        }
    except Exception as e:
        logging.error(f"Failed to query follow-up attempts: {e}")
        return {
            "attempts": [],
            "total": 0,
            "error": f"Database error: {str(e)}"
        }
