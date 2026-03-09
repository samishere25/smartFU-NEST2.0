"""
Case Management Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, case as sql_case
from typing import List, Optional
from uuid import UUID
import pandas as pd
import io
import logging

from pydantic import BaseModel, Field as PydanticField

from app.db.session import get_db

logger = logging.getLogger(__name__)
from app.models.case import AECase


class AnalyzeBody(BaseModel):
    """Optional body for analyze endpoint — carries repo form + reviewer context."""
    repo_doc_ids: List[str] = PydanticField(default_factory=list)
    reviewer_notes: str = ""
    language: str = "en"  # Follow-up language: en, hi, es, fr, de, ja, zh, pt, ar
from app.models.followup import FollowUpAttempt
from app.models.user import User
from app.schemas.case import Case, CaseCreate, CaseUpdate, CaseList
from app.core.security import get_current_active_user
from app.services.case_service import CaseService
from app.services.explainability import ExplainabilityBuilder

router = APIRouter()

@router.get("/", response_model=CaseList)
async def list_cases(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    drug: Optional[str] = None,
    event: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List cases with optional filters. High-risk cases shown first."""
    
    query = db.query(AECase)
    
    if status:
        query = query.filter(AECase.case_status == status)
    
    if risk_level:
        if risk_level == "HIGH":
            query = query.filter(AECase.seriousness_score >= 0.7)
        elif risk_level == "MEDIUM":
            query = query.filter(AECase.seriousness_score.between(0.4, 0.7))
        elif risk_level == "LOW":
            query = query.filter(AECase.seriousness_score < 0.4)
    
    # Apply drug filter (case-insensitive partial match)
    if drug:
        query = query.filter(AECase.suspect_drug.ilike(f"%{drug}%"))
    
    # Apply event filter (case-insensitive partial match)
    if event:
        query = query.filter(AECase.adverse_event.ilike(f"%{event}%"))
    
    # Sort priority - show diverse cases:
    # Mix of high, medium, and low risk cases
    query = query.order_by(
        # Mix by seriousness descending (but this will show HIGH first)
        # AECase.seriousness_score.desc(),
        # Better: order by case_id to get a natural mix
        AECase.case_id.desc()
    )
    
    total = query.count()
    cases = query.offset(skip).limit(limit).all()
    
    return CaseList(
        total=total,
        cases=cases,
        page=skip // limit + 1,
        page_size=limit
    )

@router.get("/by-primaryid/{primary_id}", response_model=Case)
async def get_case_by_primaryid(
    primary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get case by primaryid (FAERS case ID)"""
    
    case = db.query(AECase).filter(AECase.primaryid == primary_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with primaryid {primary_id} not found"
        )
    
    return case

@router.get("/{case_id}", response_model=Case)
async def get_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get case by UUID"""
    
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    return case

@router.get("/{case_id}/decision")
async def get_case_decision(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get latest AI decision and confidence for a case"""
    from app.models.followup import FollowUpDecision, CaseConfidenceHistory
    from sqlalchemy import desc
    
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Get latest decision
    latest_decision = db.query(FollowUpDecision).filter(
        FollowUpDecision.case_id == case_id
    ).order_by(desc(FollowUpDecision.created_at)).first()
    
    # Get latest confidence
    latest_confidence = db.query(CaseConfidenceHistory).filter(
        CaseConfidenceHistory.case_id == case_id
    ).order_by(desc(CaseConfidenceHistory.recorded_at)).first()
    
    if not latest_decision:
        return {
            "has_decision": False,
            "message": "No AI analysis performed yet"
        }
    
    return {
        "has_decision": True,
        "decision": latest_decision.decision_type,
        "reasoning": latest_decision.decision_reason,
        "confidence": latest_confidence.overall_confidence if latest_confidence else 0.0,
        "risk_level": latest_decision.case_risk_level,
        "response_probability": latest_decision.predicted_response_probability,
        "timestamp": latest_decision.created_at.isoformat(),
        "agent": latest_decision.agent_name
    }


@router.get("/by-primaryid/{primary_id}/analysis")
async def get_case_analysis(
    primary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the latest stored analysis for a case WITHOUT re-running AI.
    Returns the same shape as POST /analyze so frontend can use either."""
    from app.models.followup import FollowUpDecision, FollowUpAttempt, CaseConfidenceHistory
    from sqlalchemy import desc
    
    case = db.query(AECase).filter(AECase.primaryid == primary_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case with primaryid {primary_id} not found")
    
    # Get latest decision
    latest_decision = db.query(FollowUpDecision).filter(
        FollowUpDecision.case_id == case.case_id
    ).order_by(desc(FollowUpDecision.created_at)).first()
    
    if not latest_decision:
        # Even without full analysis, return reviewer + TFU questions if available
        from app.config.tfu_rules import match_tfu_rules
        early_reviewer = []
        attached_repo_doc_ids = []
        if case.review_notes:
            for line in case.review_notes.splitlines():
                line = line.strip()
                if line.startswith("[REVIEWER_QUESTION]"):
                    text = line.replace("[REVIEWER_QUESTION]", "").strip()
                    if text:
                        early_reviewer.append({
                            "field_name": f"reviewer_{len(early_reviewer)+1}",
                            "question_text": text, "question": text,
                            "criticality": "HIGH", "source": "REVIEWER_QUESTION",
                        })
                elif line.startswith("[REPO_DOC_ATTACHED]"):
                    doc_id = line.replace("[REPO_DOC_ATTACHED]", "").strip()
                    if doc_id:
                        attached_repo_doc_ids.append(doc_id)
        early_tfu = match_tfu_rules(
            case.suspect_drug or "",
            case.adverse_event or "",
            case_data={
                "suspect_drug": case.suspect_drug or "",
                "adverse_event": case.adverse_event or "",
                "patient_age": case.patient_age,
                "patient_sex": case.patient_sex,
                "event_date": str(case.event_date) if case.event_date else None,
                "event_outcome": case.event_outcome,
                "is_serious": case.is_serious,
                "drug_dose": case.drug_dose,
                "drug_route": case.drug_route,
                "dechallenge": case.dechallenge,
                "rechallenge": case.rechallenge,
                "concomitant_drugs": case.concomitant_drugs,
                "medical_history": case.medical_history,
                "reporter_country": case.reporter_country,
            },
        )

        # Resolve attached repo doc details
        attached_repo_docs = []
        if attached_repo_doc_ids:
            try:
                from app.models.repo_document import RepoDocument
                for doc_id in attached_repo_doc_ids:
                    doc = db.query(RepoDocument).filter(RepoDocument.id == doc_id, RepoDocument.is_active == True).first()
                    if doc:
                        attached_repo_docs.append({
                            "id": str(doc.id),
                            "file_name": doc.file_name,
                            "display_name": getattr(doc, 'display_name', doc.file_name),
                            "form_type": doc.form_type,
                            "questions_count": len(doc.extracted_questions) if doc.extracted_questions else 0,
                        })
            except Exception:
                pass

        return {
            "has_analysis": False,
            "case_id": str(case.case_id),
            "primaryid": case.primaryid,
            "reviewer_questions": early_reviewer,
            "tfu_questions": early_tfu,
            "ai_questions": [],
            "repo_questions": [],
            "attached_repo_docs": attached_repo_docs,
            "followup_sent": False,
            "followup_sent_count": 0,
        }
    
    # Get latest confidence
    latest_confidence = db.query(CaseConfidenceHistory).filter(
        CaseConfidenceHistory.case_id == case.case_id
    ).order_by(desc(CaseConfidenceHistory.recorded_at)).first()
    
    # Get latest follow-up attempt with questions
    latest_attempt = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case.case_id
    ).order_by(desc(FollowUpAttempt.created_at)).first()
    
    # Reconstruct questions from stored data
    questions = []
    if latest_attempt and latest_attempt.response_data:
        questions = latest_attempt.response_data.get("questions", [])

    # ── Build 4 separate question sources ─────────────────────
    from app.config.tfu_rules import match_tfu_rules

    # AI questions (from stored FollowUpAttempt)
    ai_questions = [q for q in questions]
    for q in ai_questions:
        q.setdefault("source", "AI_GENERATED")

    # Reviewer questions (from case.review_notes)
    reviewer_questions = []
    attached_repo_doc_ids_from_notes = []
    if case.review_notes:
        for line in case.review_notes.splitlines():
            line = line.strip()
            if line.startswith("[REVIEWER_QUESTION]"):
                text = line.replace("[REVIEWER_QUESTION]", "").strip()
                if text:
                    reviewer_questions.append({
                        "field_name": f"reviewer_{len(reviewer_questions)+1}",
                        "question_text": text,
                        "question": text,
                        "criticality": "HIGH",
                        "source": "REVIEWER_QUESTION",
                    })
            elif line.startswith("[REPO_DOC_ATTACHED]"):
                doc_id = line.replace("[REPO_DOC_ATTACHED]", "").strip()
                if doc_id:
                    attached_repo_doc_ids_from_notes.append(doc_id)

    # TFU mandatory questions (risk-based decision agent)
    tfu_case_data = {
        "suspect_drug": case.suspect_drug or "",
        "adverse_event": case.adverse_event or "",
        "patient_age": case.patient_age,
        "patient_sex": case.patient_sex,
        "event_date": str(case.event_date) if case.event_date else None,
        "event_outcome": case.event_outcome,
        "is_serious": case.is_serious,
        "drug_dose": case.drug_dose,
        "drug_route": case.drug_route,
        "dechallenge": case.dechallenge,
        "rechallenge": case.rechallenge,
        "concomitant_drugs": case.concomitant_drugs,
        "medical_history": case.medical_history,
        "reporter_country": case.reporter_country,
        "reporter_type": case.reporter_type,
        "therapy_start": str(case.therapy_start) if case.therapy_start else None,
        "therapy_end": str(case.therapy_end) if case.therapy_end else None,
        "indication": case.indication,
    }
    tfu_questions = match_tfu_rules(
        case.suspect_drug or "",
        case.adverse_event or "",
        case_data=tfu_case_data,
    )

    # Repo questions (only from explicitly attached docs)
    repo_questions = []
    attached_repo_docs = []
    try:
        from app.models.repo_document import RepoDocument

        # Only use docs explicitly attached on CIOMS upload page
        repo_docs = []
        if attached_repo_doc_ids_from_notes:
            repo_docs = [
                db.query(RepoDocument).filter(RepoDocument.id == did, RepoDocument.is_active == True).first()
                for did in attached_repo_doc_ids_from_notes
            ]
            repo_docs = [d for d in repo_docs if d is not None]

        for doc in repo_docs:
            attached_repo_docs.append({
                "id": str(doc.id),
                "file_name": doc.file_name,
                "display_name": getattr(doc, 'display_name', doc.file_name),
                "form_type": doc.form_type,
                "questions_count": len(doc.extracted_questions) if doc.extracted_questions else 0,
            })
            if doc.extracted_questions:
                for q in doc.extracted_questions:
                    q_dict = q if isinstance(q, dict) else {"question_text": str(q)}
                    q_dict["source"] = "REPO_FORM"
                    q_dict["source_document"] = doc.file_name
                    repo_questions.append(q_dict)
    except Exception:
        pass  # repo module may not exist — safe fallback

    # Detect if follow-up has been sent
    sent_attempt = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case.case_id,
        FollowUpAttempt.status.in_(["SENT", "AWAITING_RESPONSE"]),
    ).order_by(desc(FollowUpAttempt.created_at)).first()
    followup_sent = sent_attempt is not None
    followup_sent_count = 0
    if sent_attempt and sent_attempt.questions_sent:
        followup_sent_count = len(sent_attempt.questions_sent) if isinstance(sent_attempt.questions_sent, list) else sent_attempt.questions_count or 0

    # Build case_data (core + CIOMS-specific columns)
    case_data = {
        "primaryid": case.primaryid,
        "suspect_drug": case.suspect_drug,
        "adverse_event": case.adverse_event,
        "reporter_type": case.reporter_type,
        "patient_age": case.patient_age,
        "patient_sex": case.patient_sex,
        "drug_route": case.drug_route,
        "drug_dose": case.drug_dose,
        "event_date": case.event_date,
        "event_outcome": case.event_outcome,
        "receipt_date": str(case.receipt_date) if case.receipt_date else None,
        "reporter_country": case.reporter_country,
        "is_serious": case.is_serious,
        # CIOMS-specific fields (None for CSV-loaded cases — agents handle None gracefully)
        "patient_initials": case.patient_initials,
        "indication": case.indication,
        "therapy_start": case.therapy_start,
        "therapy_end": case.therapy_end,
        "therapy_duration": case.therapy_duration,
        "dechallenge": case.dechallenge,
        "rechallenge": case.rechallenge,
        "concomitant_drugs": case.concomitant_drugs,
        "medical_history": case.medical_history,
        "report_type": case.report_type,
        "reporter_email": case.reporter_email,
        "reporter_phone": case.reporter_phone,
        "manufacturer_name": case.manufacturer_name,
    }
    
    # Build missing_fields from questions
    missing_fields = []
    for q in questions:
        missing_fields.append({
            "field_name": q.get("field") or q.get("field_name", ""),
            "criticality": q.get("criticality", "MEDIUM"),
            "question": q.get("question", ""),
        })
    
    # Build the full analysis response (same shape as POST /analyze)
    analysis = {
        "decision": latest_decision.decision_type,
        "reasoning": latest_decision.decision_reason,
        "risk_score": case.seriousness_score or 0.0,
        "risk_level": latest_decision.case_risk_level or "UNKNOWN",
        "completeness_score": case.data_completeness_score or 0.0,
        "response_probability": latest_decision.predicted_response_probability or 0.0,
        "questions": questions,
        "missing_fields": missing_fields,
        "case_data": case_data,
        "followup_required": case.requires_followup or False,
        "stop_followup": not (case.requires_followup or False),
        "question_stats": {
            "total_generated": len(questions),
            "rl_enabled": True,
        },
    }
    
    return {
        "has_analysis": True,
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "analysis": analysis,
        "decision_id": str(latest_decision.decision_id),
        "confidence": latest_confidence.overall_confidence if latest_confidence else 0.0,
        # ── 4 separate question sources for Overview tab ──
        "ai_questions": ai_questions,
        "reviewer_questions": reviewer_questions,
        "tfu_questions": tfu_questions,
        "repo_questions": repo_questions,
        # ── attached repo documents ──
        "attached_repo_docs": attached_repo_docs,
        # ── sent state ──
        "followup_sent": followup_sent,
        "followup_sent_count": followup_sent_count,
    }


@router.post("/upload")
async def upload_cases(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk upload cases from CSV"""

    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    case_service = CaseService(db)
    result = await case_service.bulk_upload_csv(df)

    return result


@router.post("/upload-xml")
async def upload_cases_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk upload cases from an XML file (ICH E2B R2/R3 or generic flat XML)"""

    if not file.filename.lower().endswith('.xml'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only XML files are allowed"
        )

    contents = await file.read()

    try:
        from app.services.xml_intake.xml_parser import parse_xml_bytes
        cases = parse_xml_bytes(contents, filename=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    if not cases:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid cases found in the XML file. Ensure suspect_drug or adverse_event fields are present."
        )

    case_service = CaseService(db)
    result = await case_service.bulk_upload_xml(cases)
    result["filename"] = file.filename
    result["format"] = "XML"

    return result

@router.post("/by-primaryid/{primary_id}/analyze")
async def analyze_case_by_primaryid(
    primary_id: int,
    body: Optional[AnalyzeBody] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Trigger AI analysis for a case using primaryid"""
    
    case = db.query(AECase).filter(AECase.primaryid == primary_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with primaryid {primary_id} not found"
        )
    
    # Trigger AI agent workflow - CONNECTED ORCHESTRATION (Feature-1 → 2 → 3)
    from app.agents.graph import smartfu_agent_connected, smartfu_agent
    from app.agents.graph import SmartFUState
    from app.models.followup import FollowUpDecision, CaseConfidenceHistory, FollowUpAttempt
    from datetime import datetime, timedelta
    
    # Calculate REAL-TIME missing fields before AI analysis
    all_critical_fields = {
        "event_date": "CRITICAL",
        "event_outcome": "CRITICAL", 
        "patient_age": "HIGH",
        "patient_sex": "MEDIUM",
        "drug_dose": "MEDIUM",
        "drug_route": "LOW",
        "reporter_country": "MEDIUM",
        "reporter_type": "HIGH",
        "patient_initials": "CRITICAL",
    }
    
    current_missing_fields = []
    for field_name, criticality in all_critical_fields.items():
        field_value = getattr(case, field_name, None)
        if field_value is None or (isinstance(field_value, str) and field_value.strip() == ""):
            current_missing_fields.append({
                "field_name": field_name,
                "criticality": criticality
            })
    
    logger.info(f"📊 Real-time missing fields for case {case.case_id}: {[f['field_name'] for f in current_missing_fields]}")
    
    initial_state = SmartFUState(
        case_id=str(case.case_id),
        case_data={
            "primaryid": case.primaryid,
            "suspect_drug": case.suspect_drug,
            "adverse_event": case.adverse_event,
            "reporter_type": case.reporter_type,
            "patient_age": case.patient_age,
            "patient_sex": case.patient_sex,
            "drug_route": case.drug_route,
            "drug_dose": case.drug_dose,
            "event_date": case.event_date,
            "event_outcome": case.event_outcome,
            "receipt_date": str(case.receipt_date) if case.receipt_date else None,
            "reporter_country": case.reporter_country,
            "is_serious": case.is_serious,
            # CIOMS-specific fields
            "patient_initials": case.patient_initials,
            "indication": case.indication,
            "therapy_start": case.therapy_start,
            "therapy_end": case.therapy_end,
            "therapy_duration": case.therapy_duration,
            "dechallenge": case.dechallenge,
            "rechallenge": case.rechallenge,
            "concomitant_drugs": case.concomitant_drugs,
            "medical_history": case.medical_history,
            "report_type": case.report_type,
            "reporter_email": case.reporter_email,
            "reporter_phone": case.reporter_phone,
            "manufacturer_name": case.manufacturer_name,
        },
        missing_fields=current_missing_fields,  # Use REAL-TIME missing fields!
        risk_score=0.0,
        response_probability=0.0,
        decision="PENDING",
        questions=[],
        reasoning="",
        messages=[],
        # Initialize required fields for connected orchestration
        decision_history=[],
        reporter_history=[],
        case_pattern_memory={},
        agent_confidences={},
        agent_reasonings={}
    )
    
    # Use connected orchestration for Feature-1 → Feature-2 → Feature-3 flow
    try:
        result = await smartfu_agent_connected(initial_state)
    except Exception as e:
        logger.warning(f"Connected orchestration failed, falling back: {e}")
        result = await smartfu_agent(initial_state)
    
    # Store decision in database
    decision_record = FollowUpDecision(
        case_id=case.case_id,
        decision_type=result.get("decision", "UNKNOWN"),
        decision_reason=result.get("reasoning", ""),
        agent_name="SmartFU Multi-Agent System",
        confidence_score=result.get("response_probability", 0.0),
        predicted_response_probability=result.get("response_probability", 0.0),
        case_risk_level="HIGH" if result.get("risk_score", 0) >= 0.7 else "MEDIUM" if result.get("risk_score", 0) >= 0.4 else "LOW",
        escalation_required=(result.get("decision") == "ESCALATE")
    )
    db.add(decision_record)
    db.flush()  # Flush to get decision_record.decision_id immediately

    # Store confidence history
    overall_confidence = result.get("response_probability", 0.0)
    confidence_record = CaseConfidenceHistory(
        case_id=case.case_id,
        safety_confidence=result.get("risk_score", 0.0),
        data_completeness=1.0 - (len(result.get("missing_fields", [])) * 0.1),
        risk_assessment_confidence=result.get("risk_score", 0.0),
        overall_confidence=overall_confidence,
        trigger_event="ai_analysis",
        continue_followup=(result.get("decision") in ["PROCEED", "DEFER"])
    )
    db.add(confidence_record)
    
    # NOTE: Follow-up creation happens below in the filtered logic (lines 280+)
    # Don't create duplicate follow-ups here
    
    
    # Update case with AI results
    case.seriousness_score = result.get("risk_score", 0.0)  # ML risk (prioritization only)

    # Adjust completeness score based on follow-up status
    raw_completeness = result.get("completeness_score", 0.0)
    try:
        from app.services.data_completeness import DataCompletenessService
        existing_followups = (
            db.query(FollowUpAttempt)
            .filter(FollowUpAttempt.case_id == case.case_id)
            .all()
        )
        case.data_completeness_score = DataCompletenessService.adjust_for_followup_status(
            raw_completeness, existing_followups
        )
        logger.info(
            f"Completeness: raw={raw_completeness}, adjusted={case.data_completeness_score} "
            f"(followups={len(existing_followups)})"
        )
    except Exception as adj_err:
        logger.warning(f"Completeness adjustment failed, using raw: {adj_err}")
        case.data_completeness_score = raw_completeness

    case.updated_at = datetime.utcnow()

    # ── REGULATORY SERIOUSNESS (deterministic, independent of ML) ──
    # Sets case.is_serious based on ICH E2B criteria (death, hospitalization, etc.)
    # ML seriousness_score is NOT used here — it controls prioritization only.
    try:
        from app.services.regulatory_seriousness import evaluate_regulatory_seriousness
        reg_seriousness = evaluate_regulatory_seriousness({
            "event_outcome": case.event_outcome,
            "adverse_event": case.adverse_event,
            "medical_history": getattr(case, "medical_history", None),
            "is_serious": case.is_serious,  # preserve if already set from source
        })
        case.is_serious = reg_seriousness["is_serious"]
        result["regulatory_seriousness"] = reg_seriousness
        logger.info(f"Regulatory seriousness for {case.case_id}: {reg_seriousness['detail']}")
    except Exception as reg_err:
        logger.warning(f"Regulatory seriousness evaluation failed (non-blocking): {reg_err}")

    # Feature 4: Create follow-up attempt if orchestration decided follow-up is required
    followup_attempt = None  # Initialize for later verification
    followup_details = result.get("followup_details", {})
    # GATE FIX: Enter this block if AI says followup_required OR if AI generated questions
    # The AI sometimes returns followup_required=False even when it generated questions
    # (e.g. when should_stop_followup fires on completeness thresholds)
    has_ai_questions = len(result.get("questions", [])) > 0
    if result.get("followup_required", False) or has_ai_questions:
        # Check if case is 100% complete - if yes, don't create new follow-up
        try:
            # Get last attempt for iteration number
            last_attempt = db.query(FollowUpAttempt).filter(
                FollowUpAttempt.case_id == case.case_id
            ).order_by(FollowUpAttempt.created_at.desc()).first()
            
            completeness = result.get("completeness_score", 0.0)
            if completeness >= 1.0:  # 100% complete
                logger.info(f"⏹️ Follow-up stopped: Case 100% complete for {case.case_id}")
                case.requires_followup = False
                case.case_status = "COMPLETE"
                # Exit this block - don't create new follow-up
            else:
                # FIX B: Filter out already-asked and already-filled questions
                all_questions = result.get("questions", [])

                # Helper: values that DataCompletenessService treats as "missing"
                MISSING_VALUES = {None, "", "MISSING", "UNK", "UNKNOWN", "N/A", "NA"}

                def _is_field_truly_filled(value):
                    """Check if a field value is truly filled (matches DataCompletenessService logic)"""
                    if value is None:
                        return False
                    str_val = str(value).strip()
                    return str_val != "" and str_val.upper() not in MISSING_VALUES

                # Collect previously asked fields from ALL past attempts
                asked_fields = set()
                try:
                    previous_attempts = db.query(FollowUpAttempt).filter(
                        FollowUpAttempt.case_id == case.case_id
                    ).all()

                    for attempt in previous_attempts:
                        # Check response_data first (questions stored here as JSON)
                        if attempt.response_data and isinstance(attempt.response_data, dict):
                            q_list = attempt.response_data.get("questions", [])
                            for q in q_list:
                                # Handle both key formats: "field" (AI) and "field_name" (legacy)
                                field = q.get("field") or q.get("field_name")
                                if field:
                                    asked_fields.add(field)
                        # Fallback to questions_sent if response_data empty
                        elif attempt.questions_sent and isinstance(attempt.questions_sent, list):
                            for q in attempt.questions_sent:
                                if isinstance(q, dict):
                                    field = q.get("field") or q.get("field_name")
                                    if field:
                                        asked_fields.add(field)
                except Exception as e:
                    logger.warning(f"Could not fetch previous attempts: {e}")

                # Collect already-filled fields from AECase
                # MUST match DataCompletenessService logic: "UNK", "MISSING" etc. are NOT filled
                filled_fields = set()
                for field_name in ["event_date", "event_outcome", "patient_age", "patient_sex",
                                   "drug_dose", "drug_route", "reporter_country", "reporter_type"]:
                    value = getattr(case, field_name, None)
                    if _is_field_truly_filled(value):
                        filled_fields.add(field_name)

                # Apply smart filtering:
                # - CRITICAL/HIGH questions ALWAYS pass (AI flagged them, trust AI)
                # - Only exclude filled fields for non-critical questions
                # - Skip previously asked questions ONLY for non-critical
                filtered_questions = []
                for q in all_questions:
                    field = q.get("field") or q.get("field_name")
                    if not field:
                        continue
                    criticality = q.get("criticality", "MEDIUM")
                    value_score = q.get("value_score", 0.5)
                    
                    # CRITICAL/HIGH always pass through - AI says this data is needed
                    if criticality in ("CRITICAL", "HIGH") or value_score >= 0.7:
                        filtered_questions.append(q)
                        continue
                    
                    # Non-critical: skip if already asked or filled
                    if field in asked_fields or field in filled_fields:
                        continue
                    filtered_questions.append(q)
                
                logger.info(f"🔍 Question filtering for case {case.case_id}:")
                logger.info(f"   Total questions from AI: {len(all_questions)}")
                logger.info(f"   Already asked fields: {asked_fields}")
                logger.info(f"   Already filled fields: {filled_fields}")
                logger.info(f"   Filtered questions: {len(filtered_questions)}")
                
                # FIX #4: Check if ALL critical fields are filled in AECase
                CRITICAL_FIELDS = ["event_outcome", "event_date", "drug_dose", "reporter_country"]
                missing_critical = [f for f in CRITICAL_FIELDS if getattr(case, f, None) is None or str(getattr(case, f, "")).strip() == ""]
                
                if len(missing_critical) == 0:
                    logger.info(f"⏹️ FIX #4: No remaining critical fields. Follow-up stopped.")
                    case.requires_followup = False
                    case.case_status = "COMPLETE"
                elif len(filtered_questions) == 0:
                    logger.info(f"⏹️ All questions asked/filled. Follow-up stopped.")
                    case.requires_followup = False
                    case.case_status = "COMPLETE"
                else:
                    # Auto-expire stale PENDING follow-ups (>24hrs old) so they don't block new ones
                    stale_cutoff = datetime.utcnow() - timedelta(hours=24)
                    stale_pending = db.query(FollowUpAttempt).filter(
                        FollowUpAttempt.case_id == case.case_id,
                        FollowUpAttempt.status == "PENDING",
                        FollowUpAttempt.created_at < stale_cutoff
                    ).all()
                    for stale in stale_pending:
                        stale.status = "EXPIRED"
                        logger.info(f"   ♻️ Auto-expired stale PENDING attempt {stale.attempt_id}")
                    if stale_pending:
                        db.flush()
                    
                    # Check if follow-up already exists for this case
                    existing_followup = db.query(FollowUpAttempt.attempt_id).filter(
                        FollowUpAttempt.case_id == case.case_id,
                        FollowUpAttempt.status == "PENDING"
                    ).first()
                    
                    if not existing_followup:
                        # ──────────────────────────────────────────────────
                        # MULTI-CHANNEL FIX: Do NOT create a single-channel
                        # FollowUpAttempt here.  The FollowUpTrigger (called
                        # later) will create one attempt PER channel with
                        # shared decision_id.  Creating one here produces a
                        # duplicate PENDING row that never gets sent and
                        # pollutes the recently_asked filter.
                        # ──────────────────────────────────────────────────
                        
                        # Update case status (trigger still needs these flags)
                        case.requires_followup = True
                        case.case_status = "PENDING_FOLLOWUP"
                        logger.info(f"✅ Follow-up required: {len(filtered_questions)} questions — multi-channel trigger will handle attempt creation")
        except Exception as e:
            logger.error(f"Error in follow-up logic: {e}")
            # Don't create follow-up if error
    elif result.get("stop_followup", False):
        # Feature 3 adaptive stopping - no follow-up needed
        case.requires_followup = False
        case.case_status = "COMPLETE"
    elif result.get("decision") == "SKIP":
        case.requires_followup = False
        case.case_status = "COMPLETE"
    elif result.get("decision") == "ESCALATE":
        case.case_status = "ESCALATED"
    
    db.commit()
    db.refresh(case)

    # Trigger signal evaluation for this case
    from app.services.signal_service import evaluate_signals_for_case
    try:
        signal_result = await evaluate_signals_for_case(case, db)
    except Exception as sig_err:
        logger.warning(f"Signal evaluation failed (non-blocking): {sig_err}")
        signal_result = None
        try:
            db.rollback()
        except Exception:
            pass
    
    # Feature 5: Build explainability layer
    explanation = ExplainabilityBuilder.build_complete_explanation(result)
    
    # Feature 7: Log AI decision in audit trail
    from app.services.audit_service import AuditService
    
    # Store risk level and priority in case for governance
    case.risk_level = result.get("risk_level", "UNKNOWN")
    case.priority_score = result.get("priority", "MEDIUM")
    db.commit()
    
    AuditService.log_ai_decision(
        db=db,
        case_id=case.case_id,
        decision_data={
            "risk_level": result.get("risk_level"),
            "priority": result.get("priority"),
            "confidence": overall_confidence,
            "recommended_actions": result.get("recommended_actions", [])
        },
        user_id=str(current_user.user_id) if current_user else None
    )
    
    # ──────────────────────────────────────────────────────────────
    # AUTO FOLLOW-UP DISABLED — Follow-up is now MANUAL ONLY.
    # HA reviewer must click "Send Follow-Up" in the Novartis Review Dashboard.
    # The combined package (AI + reviewer + attachments) is built on-demand.
    # ──────────────────────────────────────────────────────────────
    from app.services.followup_trigger import FollowUpTrigger  # keep import for manual trigger route
    
    # CRITICAL FIX: Apply question filtering BEFORE building combined package
    # Only exclude questions for fields that are ACTUALLY FILLED in the database
    # Previously "asked but never answered" questions MUST be re-sent with correct priority
    all_questions = result.get("questions", [])
    
    # Helper: values that DataCompletenessService treats as "missing"
    MISSING_VALUES_TRIGGER = {None, "", "MISSING", "UNK", "UNKNOWN", "N/A", "NA"}

    def _is_truly_filled(value):
        """Check if a field value is truly filled (matches DataCompletenessService logic)"""
        if value is None:
            return False
        str_val = str(value).strip()
        return str_val != "" and str_val.upper() not in MISSING_VALUES_TRIGGER

    # Collect recently asked fields ONLY from very recent attempts (last 1 hour)
    # This prevents spam but allows re-asking unanswered questions after some time
    from datetime import datetime, timedelta
    
    # ──────────────────────────────────────────────────────────────────────
    # MULTI-CHANNEL FIX: Auto-expire all active attempts on re-analyze
    # Re-Analyze is an EXPLICIT user action → "I want fresh follow-ups."
    # Old PENDING / SENT / AWAITING_RESPONSE attempts are superseded;
    # the FollowUpTrigger below will create fresh multi-channel ones.
    # Without this, multi-channel sister attempts (EMAIL+PHONE+WHATSAPP)
    # block ALL questions via the recently_asked filter ⟹ 0 questions ⟹
    # no follow-up fires on re-analyze.
    # ──────────────────────────────────────────────────────────────────────
    try:
        old_active_attempts = db.query(FollowUpAttempt).filter(
            FollowUpAttempt.case_id == case.case_id,
            FollowUpAttempt.status.in_(["PENDING", "SENT", "AWAITING_RESPONSE"])
        ).all()
        if old_active_attempts:
            for old_attempt in old_active_attempts:
                old_attempt.status = "EXPIRED"
                old_attempt.stop_reason = "Superseded by re-analysis"
            db.flush()
            logger.info(f"♻️ Auto-expired {len(old_active_attempts)} active attempts on re-analyze")
    except Exception as e:
        logger.warning(f"Could not expire old attempts on re-analyze: {e}")

    current_attempt_id = followup_attempt.attempt_id if followup_attempt else None
    recently_asked_fields = set()
    confirmed_unanswered_fields = set()  # Fields asked but reporter skipped — MUST be re-asked
    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_attempts = db.query(FollowUpAttempt).filter(
            FollowUpAttempt.case_id == case.case_id,
            FollowUpAttempt.status.in_(["PENDING", "SENT", "AWAITING_RESPONSE"]),
            FollowUpAttempt.sent_at >= one_hour_ago  # Only very recent
        ).all()

        for attempt in recent_attempts:
            # Skip the attempt we JUST created in this same request (self-blocking fix)
            if current_attempt_id and attempt.attempt_id == current_attempt_id:
                continue
            if attempt.response_data and isinstance(attempt.response_data, dict):
                q_list = attempt.response_data.get("questions", [])
                for q in q_list:
                    field = q.get("field") or q.get("field_name")
                    if field:
                        recently_asked_fields.add(field)
            elif attempt.questions_sent and isinstance(attempt.questions_sent, list):
                for q in attempt.questions_sent:
                    if isinstance(q, dict):
                        field = q.get("field") or q.get("field_name")
                        if field:
                            recently_asked_fields.add(field)
        
        # Collect confirmed unanswered fields from PARTIAL_RESPONSE / RESPONDED attempts
        # These fields were asked but reporter skipped — they MUST be allowed through
        partial_attempts = db.query(FollowUpAttempt).filter(
            FollowUpAttempt.case_id == case.case_id,
            FollowUpAttempt.status.in_(["PARTIAL_RESPONSE", "RESPONDED"])
        ).all()
        for attempt in partial_attempts:
            if attempt.response_data and isinstance(attempt.response_data, dict):
                # Check explicit unanswered list
                unanswered_list = attempt.response_data.get("unanswered", [])
                for u in unanswered_list:
                    field = u.get("field") or u.get("field_name")
                    if field:
                        confirmed_unanswered_fields.add(field)
                # Also cross-reference questions vs answers
                q_list = attempt.response_data.get("questions", [])
                a_list = attempt.response_data.get("answers", [])
                answered_set = {a.get("field_name") or a.get("field") for a in a_list if a.get("field_name") or a.get("field")}
                for q in q_list:
                    field = q.get("field") or q.get("field_name")
                    if field and field not in answered_set:
                        confirmed_unanswered_fields.add(field)
        
        # CRITICAL: Remove confirmed unanswered fields from the skip list
        # These MUST be re-asked even if they were recently sent
        if confirmed_unanswered_fields:
            logger.info(f"🔄 Unanswered fields exempt from recently_asked filter: {confirmed_unanswered_fields}")
            recently_asked_fields -= confirmed_unanswered_fields
    except Exception as e:
        logger.warning(f"Could not fetch recent attempts: {e}")

    # STEP 5: REFETCH CASE FROM DATABASE TO GET FRESH DATA
    logger.info("="*80)
    logger.info("🔄 REFETCHING CASE FROM DATABASE (ensure fresh data)")
    db.refresh(case)
    logger.info(f"   Case {case.case_id} refreshed")
    logger.info("="*80)

    # Collect already-filled fields - MUST match DataCompletenessService logic
    # "UNK", "MISSING", "N/A" etc. are NOT considered filled
    logger.info("="*80)
    logger.info("🔍 STEP 5: BUILDING FILLED FIELDS LIST")
    filled_fields = set()
    for field_name in ["event_date", "event_outcome", "patient_age", "patient_sex",
                       "drug_dose", "drug_route", "reporter_country", "reporter_type"]:
        value = getattr(case, field_name, None)
        if _is_truly_filled(value):
            filled_fields.add(field_name)
            logger.info(f"   ✅ {field_name} = {value} (FILLED)")
        else:
            logger.info(f"   ❌ {field_name} = {value} (MISSING/EMPTY/UNK)")

    logger.info(f"   Total filled fields: {filled_fields}")
    logger.info(f"   Recently asked fields (last 1hr): {recently_asked_fields}")
    logger.info("="*80)
    
    # B. SMART FILTERING: 
    # - CRITICAL/HIGH questions ALWAYS pass through (AI flagged them as needing data, trust the AI)
    # - Non-critical fields: exclude if already filled in DB
    # - For unfilled fields: only skip if asked in last 1 hour (prevent spam)
    logger.info("="*80)
    logger.info("🔍 STEP 5: SMART QUESTION FILTERING")
    filtered_questions = []
    for q in all_questions:
        field = q.get("field") or q.get("field_name")
        if not field:
            logger.warning(f"   ⚠️ Question missing field identifier: {q}")
            continue
        
        criticality = q.get("criticality", "MEDIUM")
        value_score = q.get("value_score", 0.5)
        
        # RULE 1: CRITICAL/HIGH questions ALWAYS pass through
        # The AI generated these knowing the field values - it wants confirmation/better data
        if criticality in ("CRITICAL", "HIGH") or value_score >= 0.7:
            # Even CRITICAL can be skipped if asked very recently (last 1 hour) to prevent spam
            if field in recently_asked_fields:
                logger.info(f"   ⏳ SKIPPING {field}: {criticality} priority but asked within last 1hr")
                continue
            filtered_questions.append(q)
            logger.info(f"   ✅ KEEPING {field}: {criticality} priority (value={value_score}) - AI says ask")
            continue
        
        # RULE 2: Non-critical fields: exclude if already filled in database
        if field in filled_fields:
            logger.info(f"   ❌ EXCLUDING {field}: {criticality} priority, already filled in DB")
            continue
        
        # RULE 3: For MEDIUM/LOW unfilled questions, skip if asked very recently (last 1 hour)
        if field in recently_asked_fields:
            logger.info(f"   ⏳ SKIPPING {field}: {criticality} priority, asked recently (within 1hr)")
            continue
        
        filtered_questions.append(q)
        logger.info(f"   ✅ KEEPING {field}: {criticality} priority (value={value_score})")
    
    logger.info(f"   Result: {len(filtered_questions)} questions after smart filtering")
    logger.info("="*80)
    
    logger.info(f"🔍 PRE-TRIGGER FILTERING for case {case.case_id}:")
    logger.info(f"   AI generated: {len(all_questions)} questions")
    
    # DEBUG: Show each AI question's field name
    for idx, q in enumerate(all_questions):
        field = q.get("field") or q.get("field_name")
        logger.info(f"      Q{idx+1}: field='{field}' question='{q.get('question', '')[:50]}...'")
    
    logger.info(f"   Already asked: {recently_asked_fields}")
    logger.info(f"   Already filled: {filled_fields}")
    logger.info(f"   Will send: {len(filtered_questions)} NEW questions")
    
    # DEBUG: Show which questions passed filtering
    for idx, q in enumerate(filtered_questions):
        field = q.get("field") or q.get("field_name")
        logger.info(f"      ✅ Sending Q{idx+1}: field='{field}'")
    
    # ──────────────────────────────────────────────────────────────
    # MERGE SUPPLEMENTARY QUESTIONS (reviewer + checklist + attachments)
    # Combines AI-generated questions with reviewer notes and
    # checklist PDF items into ONE consolidated follow-up package.
    # ──────────────────────────────────────────────────────────────
    try:
        from app.services.combined_followup import get_supplementary_questions
        existing_fields = {q.get("field") or q.get("field_name") for q in filtered_questions if q.get("field") or q.get("field_name")}
        supplementary = get_supplementary_questions(case, db, existing_fields)

        # Append reviewer questions (as-is, not modified by AI)
        if supplementary.get("reviewer_questions"):
            filtered_questions.extend(supplementary["reviewer_questions"])
            logger.info(f"📋 Added {len(supplementary['reviewer_questions'])} reviewer questions")

        # Append checklist items (extracted from TAFU/Pregnancy PDFs)
        if supplementary.get("checklist_questions"):
            filtered_questions.extend(supplementary["checklist_questions"])
            logger.info(f"📋 Added {len(supplementary['checklist_questions'])} checklist items from PDFs")

        # Store attachments in result — flows into response_data on FollowUpAttempt
        if supplementary.get("attachments"):
            result["followup_attachments"] = supplementary["attachments"]
            logger.info(f"📎 {len(supplementary['attachments'])} PDF attachments included")
    except Exception as supp_err:
        # Non-blocking: if supplementary fails, AI questions still go through
        logger.error(f"⚠️ Supplementary questions failed: {supp_err}", exc_info=True)

    # ──────────────────────────────────────────────────────────────
    # MERGE REPO DOCUMENT QUESTIONS — Smart AI Filter
    # Uses Mistral AI to pick 5-15 relevant questions from the full
    # repo form (e.g. 63-question TAFU checklist) based on the
    # case's missing fields. PDFs are also attached for the reporter.
    # ──────────────────────────────────────────────────────────────
    repo_attachments = []
    try:
        from app.models.repo_document import RepoDocument
        from app.services.repo_question_filter import filter_repo_questions_for_case

        all_repo_questions = []

        # Check CIOMS-page attached repo doc IDs from review_notes first
        attached_repo_doc_ids_from_notes = []
        if case.review_notes:
            for rl in case.review_notes.splitlines():
                rl = rl.strip()
                if rl.startswith("[REPO_DOC_ATTACHED]"):
                    did = rl.replace("[REPO_DOC_ATTACHED]", "").strip()
                    if did:
                        attached_repo_doc_ids_from_notes.append(did)

        # Priority: 1) review_notes tags, 2) body.repo_doc_ids, 3) ALL active (PDF-only)
        use_questions = True  # Extract questions from selected docs
        if attached_repo_doc_ids_from_notes:
            doc_id_list = attached_repo_doc_ids_from_notes
            logger.info(f"📂 REPO: Using {len(doc_id_list)} attached repo docs from review_notes")
        elif body and body.repo_doc_ids:
            doc_id_list = body.repo_doc_ids
            logger.info(f"📂 REPO: Using {len(doc_id_list)} repo docs from request body")
        else:
            # Fallback: attach ALL active repo PDFs but DON'T extract questions
            doc_id_list = None
            use_questions = False
            logger.info("📂 REPO: No explicit selection — will attach ALL active repo PDFs (no questions)")

        if doc_id_list is not None:
            for doc_id_str in doc_id_list:
                doc = db.query(RepoDocument).filter(
                    RepoDocument.id == doc_id_str,
                    RepoDocument.is_active == True,
                ).first()
                if not doc:
                    logger.warning(f"Repo document {doc_id_str} not found, skipping")
                    continue

                if use_questions and doc.extracted_questions:
                    for q in doc.extracted_questions:
                        q_dict = q if isinstance(q, dict) else {"question_text": str(q)}
                        q_dict["source_document"] = doc.file_name
                        all_repo_questions.append(q_dict)

                repo_attachments.append({
                    "document_type": doc.form_type,
                    "file_name": doc.file_name,
                    "file_path": doc.file_path,
                    "document_id": str(doc.id),
                })
        else:
            # Fallback: load all active repo docs as attachment-only
            all_active = db.query(RepoDocument).filter(RepoDocument.is_active == True).all()
            for doc in all_active:
                repo_attachments.append({
                    "document_type": doc.form_type,
                    "file_name": doc.file_name,
                    "file_path": doc.file_path,
                    "document_id": str(doc.id),
                })
            logger.info(f"📂 REPO: Loaded {len(all_active)} active repo PDFs as attachments (no questions)")

        # Smart filter: use Mistral AI to pick only the relevant questions
        if all_repo_questions:
            missing_fields = result.get("missing_fields_detailed", result.get("missing_fields", []))
            # Normalize missing_fields to list-of-dicts if it's list-of-strings
            if missing_fields and isinstance(missing_fields[0], str):
                missing_fields = [{"field": f, "criticality": "MEDIUM"} for f in missing_fields]

            case_ctx = {
                "suspect_drug": case.suspect_drug,
                "adverse_event": case.adverse_event,
                "patient_age": case.patient_age,
                "patient_sex": case.patient_sex,
                "event_outcome": case.event_outcome,
            }
            smart_questions = filter_repo_questions_for_case(
                all_repo_questions, missing_fields, case_ctx
            )
            filtered_questions.extend(smart_questions)
            logger.info(
                f"📋 Repo: {len(all_repo_questions)} total → {len(smart_questions)} AI-filtered questions"
            )

        if repo_attachments:
            result["followup_attachments"] = result.get("followup_attachments", []) + repo_attachments
        logger.info(f"📎 Attached {len(repo_attachments)} repo form PDFs to follow-up")
    except Exception as repo_err:
        logger.error(f"⚠️ Repo document processing failed: {repo_err}", exc_info=True)

    # ──────────────────────────────────────────────────────────────
    # MERGE REVIEWER NOTES (from CiomsUploadPage textarea)
    # ──────────────────────────────────────────────────────────────
    logger.info(f"🔍 REVIEWER NOTES CHECK: body={body is not None}, reviewer_notes='{getattr(body, 'reviewer_notes', 'N/A') if body else 'NO BODY'}'")
    if body and body.reviewer_notes and body.reviewer_notes.strip():
        try:
            from app.services.combined_followup import convert_reviewer_notes_to_questions
            notes = [n.strip() for n in body.reviewer_notes.strip().split("\n") if n.strip()]
            logger.info(f"📝 Reviewer notes parsed: {len(notes)} notes → {notes}")
            if notes:
                case_data_for_notes = {
                    "suspect_drug": case.suspect_drug,
                    "adverse_event": case.adverse_event,
                    "patient_age": case.patient_age,
                }
                reviewer_items = convert_reviewer_notes_to_questions(
                    notes=notes,
                    case_data=case_data_for_notes,
                    existing_questions=filtered_questions,
                )
                logger.info(f"📝 AI conversion returned {len(reviewer_items)} reviewer items")

                # SAFETY NET: if AI conversion returned 0 items, use raw notes directly
                if not reviewer_items:
                    logger.warning("⚠️ AI conversion returned 0 items — using raw notes as questions")
                    reviewer_items = []
                    for i, note in enumerate(notes):
                        reviewer_items.append({
                            "field_name": f"reviewer_note_{i+1}",
                            "question": note,
                            "question_text": note,
                            "criticality": "HIGH",
                            "source": "REVIEWER_NOTE_RAW",
                            "original_note": note,
                        })

                for ri in reviewer_items:
                    ri["source"] = "REVIEWER_NOTE_AI"
                    # Ensure question_text is set (email renderer uses this key first)
                    if "question_text" not in ri and "question" in ri:
                        ri["question_text"] = ri["question"]
                    logger.info(f"   📋 Reviewer Q: {ri.get('question_text', ri.get('question', '???'))[:80]}")
                filtered_questions.extend(reviewer_items)
                logger.info(f"📋 Added {len(reviewer_items)} reviewer note questions (total now: {len(filtered_questions)})")
            else:
                logger.warning("⚠️ Reviewer notes were non-empty but parsed to 0 notes")
        except Exception as rn_err:
            logger.error(f"⚠️ Reviewer note conversion EXCEPTION: {rn_err}", exc_info=True)
            # LAST RESORT: Even if everything fails, add raw notes as questions
            try:
                raw_notes = [n.strip() for n in body.reviewer_notes.strip().split("\n") if n.strip()]
                for i, note in enumerate(raw_notes):
                    filtered_questions.append({
                        "field_name": f"reviewer_note_{i+1}",
                        "question": note,
                        "question_text": note,
                        "criticality": "HIGH",
                        "source": "REVIEWER_NOTE_AI",
                        "original_note": note,
                    })
                logger.info(f"📋 FALLBACK: Added {len(raw_notes)} raw reviewer notes as questions")
            except Exception:
                logger.error("❌ Complete reviewer note processing failure", exc_info=True)
    else:
        logger.info("⏭️ No reviewer notes in request body — skipping reviewer merge")

    # ──────────────────────────────────────────────────────────────
    # REORDER: Put REVIEWER and REPO questions FIRST so they're asked
    # before AI questions can push completeness to 100% and trigger
    # early termination in the follow-up agent form.
    # ──────────────────────────────────────────────────────────────
    if filtered_questions:
        priority_qs = []  # Reviewer + Repo + Checklist (asked first)
        regular_qs = []   # AI-generated (asked after)
        for q in filtered_questions:
            src = (q.get("source") or "").upper()
            if "REVIEWER" in src or "REPO" in src or "CHECKLIST" in src:
                priority_qs.append(q)
            else:
                regular_qs.append(q)
        if priority_qs:
            filtered_questions = priority_qs + regular_qs
            logger.info(f"🔀 Reordered: {len(priority_qs)} reviewer/repo Qs moved to front, {len(regular_qs)} AI Qs after")

    # Store language preference in result for downstream services
    followup_language = body.language if body else "en"
    result["followup_language"] = followup_language
    logger.info(f"🌐 Follow-up language: {followup_language}")

    # CRITICAL OVERRIDE: If we have filtered questions to send, force followup_required=True
    # The AI agent sometimes returns followup_required=False even when there are valid questions
    # (e.g. due to completeness thresholds in should_stop_followup)
    if filtered_questions and len(filtered_questions) > 0:
        result["followup_required"] = True
        result["stop_followup"] = False
        logger.info(f"✅ OVERRIDE: Forcing followup_required=True because {len(filtered_questions)} questions exist")

    # Store filtered questions in result for the combined package builder
    result["filtered_questions"] = filtered_questions
    result["questions"] = filtered_questions  # Update the result with filtered questions

    # DEBUG: Log all questions by source before triggering follow-up
    logger.info(f"📊 FINAL QUESTION SUMMARY: {len(filtered_questions)} total questions")
    source_counts = {}
    for q in filtered_questions:
        src = q.get("source", "AI_GENERATED")
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, cnt in source_counts.items():
        logger.info(f"   📌 Source '{src}': {cnt} questions")
    for idx, q in enumerate(filtered_questions):
        logger.info(f"   Q{idx+1}: [{q.get('source', 'AI')}] {q.get('question_text', q.get('question', '???'))[:70]}")

    # ──────────────────────────────────────────────────────────────
    # STORE AI QUESTIONS — No auto-send.
    # Create a FollowUpAttempt with status="AI_READY" so GET /analysis
    # can return the questions. Actual sending happens via analyze-and-send.
    # ──────────────────────────────────────────────────────────────
    followup_result = {"followup_created": False, "reason": "AI analysis stored, manual send via Analyze button"}
    if filtered_questions and len(filtered_questions) > 0:
        import uuid as _uuid
        ai_store_attempt = FollowUpAttempt(
            attempt_id=_uuid.uuid4(),
            case_id=case.case_id,
            decision_id=decision_record.decision_id if decision_record else None,
            iteration_number=1,
            attempt_number=1,
            channel="NONE",
            questions_sent=filtered_questions,
            questions_count=len(filtered_questions),
            response_data={"questions": filtered_questions},
            decision=result.get("decision", "ASK"),
            reasoning="AI analysis complete — questions stored, awaiting manual follow-up trigger",
            status="AI_READY",
            sent_at=datetime.utcnow(),
        )
        db.add(ai_store_attempt)
        db.commit()
        followup_result["questions_stored"] = len(filtered_questions)
        logger.info(f"✅ Stored {len(filtered_questions)} AI questions in FollowUpAttempt (status=AI_READY, no send)")
    else:
        followup_result = {
            "followup_created": False,
            "reason": "No questions to store",
            "questions_ready": 0,
            "channel": None
        }

    # AUTO-INITIALIZE LIFECYCLE TRACKING (Feature-4 integration)
    # This ensures lifecycle tracks the case automatically when analyzed
    lifecycle_result = None
    try:
        from app.services.lifecycle_db_service import LifecycleDBService
        lifecycle_service = LifecycleDBService(db)

        # Determine seriousness level from REGULATORY evaluation (not ML risk)
        # This drives lifecycle deadlines: 7-day (high/critical) vs 15-day (medium/low)
        reg_result = result.get("regulatory_seriousness")
        if reg_result:
            from app.services.regulatory_seriousness import get_seriousness_level
            seriousness = get_seriousness_level(reg_result)
        else:
            # Fallback to ML risk if regulatory eval didn't run
            risk_score_val = result.get("risk_score", 0.0)
            if risk_score_val >= 0.8:
                seriousness = "critical"
            elif risk_score_val >= 0.6:
                seriousness = "high"
            elif risk_score_val >= 0.3:
                seriousness = "medium"
            else:
                seriousness = "low"

        # Initialize lifecycle (idempotent - returns existing if already initialized)
        lifecycle = lifecycle_service.initialize_lifecycle(
            case_id=str(case.case_id),
            reporter_type=case.reporter_type or "OT",
            seriousness_level=seriousness,
            initial_completeness=result.get("completeness_score", 0.0)
        )

        # Auto-record follow-up sent if one was just triggered
        if followup_result and followup_result.get("followup_created"):
            lifecycle = lifecycle_service.record_followup_sent(
                lifecycle=lifecycle,
                questions_sent=filtered_questions,
                channel=followup_result.get("channel", "EMAIL"),
                sent_to=followup_result.get("communication_result", {}).get("to_email")
            )
            logger.info(f"✅ Lifecycle auto-updated: follow-up #{lifecycle.attempt_count} recorded for case {case.case_id}")

        lifecycle_result = lifecycle_service.get_lifecycle_summary(lifecycle)
        logger.info(f"✅ Lifecycle auto-initialized for case {case.case_id}: {seriousness}")
    except Exception as lifecycle_err:
        logger.warning(f"⚠️ Lifecycle auto-init failed (non-critical): {lifecycle_err}")
        try:
            db.rollback()
        except Exception:
            pass

    # Safely read decision_id before returning (avoid lazy-load after rollback)
    decision_id_str = str(decision_record.decision_id) if decision_record and hasattr(decision_record, 'decision_id') and decision_record.decision_id else None

    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "analysis": result,
        "decision_id": decision_id_str,
        "confidence": overall_confidence,
        "signals": signal_result,
        "explainability": explanation,
        "governance": {
            "ai_generated": True,
            "human_final": False,
            "requires_review": True
        },
        "regulatory_seriousness": result.get("regulatory_seriousness"),
        "automated_followup": followup_result,
        "lifecycle": lifecycle_result
    }

class ReviewerQuestionsBody(BaseModel):
    """Body for saving reviewer questions."""
    questions: List[str] = PydanticField(default_factory=list)


@router.post("/{case_id}/save-reviewer-questions")
async def save_reviewer_questions(
    case_id: UUID,
    body: ReviewerQuestionsBody,
    db: Session = Depends(get_db),
    _user = Depends(get_current_active_user),
):
    """Save reviewer questions to case.review_notes. Does NOT trigger follow-up."""
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Store as newline-separated block tagged with REVIEWER_QUESTION
    lines = [q.strip() for q in body.questions if q.strip()]
    block = "\n".join(f"[REVIEWER_QUESTION] {l}" for l in lines)
    existing = (case.review_notes or "").strip()
    case.review_notes = f"{existing}\n{block}".strip() if existing else block
    db.commit()
    return {"status": "saved", "question_count": len(lines)}


class AttachRepoDocsBody(BaseModel):
    """Body for attaching repo documents to a case."""
    repo_doc_ids: List[str] = PydanticField(default_factory=list)


@router.post("/{case_id}/attach-repo-docs")
async def attach_repo_docs(
    case_id: UUID,
    body: AttachRepoDocsBody,
    db: Session = Depends(get_db),
    _user = Depends(get_current_active_user),
):
    """Persist selected repository document IDs to case.review_notes as [REPO_DOC_ATTACHED] tags."""
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Remove any existing REPO_DOC_ATTACHED lines
    existing_lines = (case.review_notes or "").splitlines()
    cleaned = [l for l in existing_lines if not l.strip().startswith("[REPO_DOC_ATTACHED]")]

    # Append new REPO_DOC_ATTACHED tags
    new_tags = [f"[REPO_DOC_ATTACHED] {doc_id}" for doc_id in body.repo_doc_ids if doc_id.strip()]
    all_lines = cleaned + new_tags
    case.review_notes = "\n".join(all_lines).strip() or None
    db.commit()

    return {"status": "saved", "attached_count": len(new_tags)}


class AnalyzeAndSendBody(BaseModel):
    """Body for the analyze-and-send endpoint."""
    repo_doc_ids: List[str] = PydanticField(default_factory=list)
    language: str = "en"


@router.post("/{case_id}/analyze-and-send")
async def analyze_and_send(
    case_id: UUID,
    body: Optional[AnalyzeAndSendBody] = None,
    db: Session = Depends(get_db),
    _user = Depends(get_current_active_user),
):
    """
    Merge 4 question sources → freeze → send follow-up.
    Order: 1) Reviewer  2) TFU Mandatory  3) Repo  4) AI Generated
    """
    from app.models.followup import FollowUpAttempt, FollowUpDecision, CaseConfidenceHistory
    from app.services.followup_trigger import FollowUpTrigger
    from app.config.tfu_rules import match_tfu_rules, apply_tfu_gate
    from datetime import datetime

    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # ── 1. Load AI questions from latest FollowUpAttempt ──────────
    from sqlalchemy import desc
    latest_attempt = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case.case_id
    ).order_by(desc(FollowUpAttempt.created_at)).first()
    ai_questions = []
    if latest_attempt and latest_attempt.response_data:
        ai_questions = latest_attempt.response_data.get("questions", [])
    # Tag source
    for q in ai_questions:
        q.setdefault("source", "AI_GENERATED")

    # ── 2. Load reviewer saved questions + attached repo IDs from case.review_notes ───
    reviewer_questions = []
    attached_repo_doc_ids = []
    if case.review_notes:
        for line in case.review_notes.splitlines():
            line = line.strip()
            if line.startswith("[REVIEWER_QUESTION]"):
                text = line.replace("[REVIEWER_QUESTION]", "").strip()
                if text:
                    reviewer_questions.append({
                        "field_name": f"reviewer_{len(reviewer_questions)+1}",
                        "question_text": text,
                        "question": text,
                        "criticality": "HIGH",
                        "source": "REVIEWER_QUESTION",
                    })
            elif line.startswith("[REPO_DOC_ATTACHED]"):
                doc_id = line.replace("[REPO_DOC_ATTACHED]", "").strip()
                if doc_id:
                    attached_repo_doc_ids.append(doc_id)

    # ── 3. Apply TFU matching (risk-based decision agent) ─────────
    case_data_for_tfu = {
        "suspect_drug": case.suspect_drug or "",
        "adverse_event": case.adverse_event or "",
        "patient_age": case.patient_age,
        "patient_sex": case.patient_sex,
        "event_date": str(case.event_date) if case.event_date else None,
        "event_outcome": case.event_outcome,
        "is_serious": case.is_serious,
        "drug_dose": case.drug_dose,
        "drug_route": case.drug_route,
        "dechallenge": case.dechallenge,
        "rechallenge": case.rechallenge,
        "concomitant_drugs": case.concomitant_drugs,
        "medical_history": case.medical_history,
        "reporter_country": case.reporter_country,
        "reporter_type": case.reporter_type,
        "therapy_start": str(case.therapy_start) if case.therapy_start else None,
        "therapy_end": str(case.therapy_end) if case.therapy_end else None,
        "indication": case.indication,
    }
    tfu_questions = match_tfu_rules(
        case.suspect_drug or "",
        case.adverse_event or "",
        case_data=case_data_for_tfu,
    )
    logger.info(f"🔍 TFU DEBUG: drug='{case.suspect_drug}', event='{case.adverse_event}' → {len(tfu_questions)} TFU questions (risk-based)")

    # ── 4. Load repository extracted questions ────────────────────
    # Priority: 1) attached_repo_doc_ids from review_notes, 2) body.repo_doc_ids, 3) ALL active
    repo_questions = []
    repo_attachments = []
    try:
        from app.models.repo_document import RepoDocument
        from app.services.repo_question_filter import filter_repo_questions_for_case

        # Only use explicitly attached docs (from CIOMS page or request body)
        repo_docs = []
        if attached_repo_doc_ids:
            repo_docs = [
                db.query(RepoDocument).filter(
                    RepoDocument.id == doc_id_str,
                    RepoDocument.is_active == True,
                ).first()
                for doc_id_str in attached_repo_doc_ids
            ]
            repo_docs = [d for d in repo_docs if d is not None]
            logger.info(f"📂 REPO DEBUG: Using {len(repo_docs)} attached repo docs from review_notes")
        elif body and body.repo_doc_ids:
            repo_docs = [
                db.query(RepoDocument).filter(
                    RepoDocument.id == doc_id_str,
                    RepoDocument.is_active == True,
                ).first()
                for doc_id_str in body.repo_doc_ids
            ]
            repo_docs = [d for d in repo_docs if d is not None]
            logger.info(f"📂 REPO DEBUG: Using {len(repo_docs)} repo docs from request body")
        else:
            # FALLBACK: No explicit selection → attach ALL active repo PDFs
            # (questions are NOT extracted — only PDF files go as email attachments)
            repo_docs = db.query(RepoDocument).filter(RepoDocument.is_active == True).all()
            logger.info(f"📂 REPO DEBUG: No explicit selection — fallback to ALL {len(repo_docs)} active repo docs (PDF-only, no questions)")

        # Separate handling: explicit selection gets questions + attachments,
        # fallback (no selection) gets attachments only
        use_questions = bool(attached_repo_doc_ids or (body and body.repo_doc_ids))

        all_repo_qs = []
        for doc in repo_docs:
            if use_questions and doc.extracted_questions:
                for q in doc.extracted_questions:
                    q_dict = q if isinstance(q, dict) else {"question_text": str(q)}
                    q_dict["source_document"] = doc.file_name
                    all_repo_qs.append(q_dict)
            repo_attachments.append({
                "document_type": doc.form_type,
                "file_name": doc.file_name,
                "file_path": doc.file_path,
                "document_id": str(doc.id),
            })
        logger.info(f"📂 REPO DEBUG: {len(repo_docs)} docs → {len(all_repo_qs)} raw repo questions extracted")

        if all_repo_qs:
            missing_fields = [{"field": q.get("field") or q.get("field_name", ""), "criticality": "MEDIUM"} for q in ai_questions]
            case_ctx = {
                "suspect_drug": case.suspect_drug,
                "adverse_event": case.adverse_event,
                "patient_age": case.patient_age,
                "patient_sex": case.patient_sex,
                "event_outcome": case.event_outcome,
            }
            repo_questions = filter_repo_questions_for_case(all_repo_qs, missing_fields, case_ctx)
            for q in repo_questions:
                q["source"] = "REPO_FORM"
            logger.info(f"📂 REPO DEBUG: After filter → {len(repo_questions)} repo questions kept")
    except Exception as e:
        logger.warning(f"Repo question loading failed: {e}", exc_info=True)

    # ── 5. Merge in strict priority order (deduplicate) ───────────
    seen_fields = set()
    merged_raw = []
    for bucket in [reviewer_questions, tfu_questions, repo_questions, ai_questions]:
        for q in bucket:
            field = q.get("field_name") or q.get("field") or q.get("question_text", "")[:40]
            if field not in seen_fields:
                seen_fields.add(field)
                merged_raw.append(q)

    logger.info(f"📊 Analyze-and-send merge (raw): reviewer={len(reviewer_questions)}, tfu={len(tfu_questions)}, repo={len(repo_questions)}, ai={len(ai_questions)} → raw={len(merged_raw)}")

    # ── 5b. Apply TFU gate — remove filled fields & cap at 5 ─────
    merged = apply_tfu_gate(merged_raw, case_data_for_tfu)
    logger.info(f"📊 Analyze-and-send after TFU gate: {len(merged_raw)} → {len(merged)} questions (max 5)")

    if not merged:
        return {"status": "no_questions", "message": "No questions to send"}

    # ── 6. Expire old active attempts ─────────────────────────────
    old = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case.case_id,
        FollowUpAttempt.status.in_(["PENDING", "SENT", "AWAITING_RESPONSE"]),
    ).all()
    for o in old:
        o.status = "EXPIRED"
        o.stop_reason = "Superseded by analyze-and-send"
    if old:
        db.flush()

    # ── 7. Build result dict for FollowUpTrigger ──────────────────
    latest_decision = db.query(FollowUpDecision).filter(
        FollowUpDecision.case_id == case.case_id
    ).order_by(desc(FollowUpDecision.created_at)).first()

    result_for_trigger = {
        "decision": latest_decision.decision_type if latest_decision else "ASK",
        "risk_score": case.seriousness_score or 0.0,
        "completeness_score": case.data_completeness_score or 0.0,
        "questions": merged,
        "filtered_questions": merged,
        "followup_required": True,
        "stop_followup": False,
        "followup_language": body.language if body else "en",
    }
    if repo_attachments:
        result_for_trigger["followup_attachments"] = repo_attachments

    # ── 8. Trigger FollowUpTrigger.send() ─────────────────────────
    case.requires_followup = True
    case.case_status = "PENDING_FOLLOWUP"
    db.commit()

    followup_result = None
    try:
        followup_result = await FollowUpTrigger.trigger_automated_followup(
            db=db,
            case=case,
            analysis_result=result_for_trigger,
            questions=merged,
            user_id=None,
        )
        logger.info(f"✅ Analyze-and-send follow-up triggered: {followup_result}")
    except Exception as fu_err:
        logger.error(f"❌ Analyze-and-send follow-up failed: {fu_err}")
        followup_result = {
            "followup_created": False,
            "reason": str(fu_err),
            "questions_ready": len(merged),
        }

    return {
        "status": "sent",
        "merged_questions": len(merged),
        "sources": {
            "reviewer": len(reviewer_questions),
            "tfu": len(tfu_questions),
            "repo": len(repo_questions),
            "ai": len(ai_questions),
        },
        "followup_result": followup_result,
    }


@router.post("/{case_id}/analyze")
async def analyze_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger AI analysis for a case"""
    
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Trigger AI agent workflow - CONNECTED ORCHESTRATION
    from app.agents.graph import smartfu_agent_connected, smartfu_agent
    from app.agents.graph import SmartFUState
    
    initial_state = SmartFUState(
        case_id=str(case_id),
        case_data={
            "primaryid": case.primaryid,
            "suspect_drug": case.suspect_drug,
            "adverse_event": case.adverse_event,
            "reporter_type": case.reporter_type,
            "patient_age": case.patient_age,
            "patient_sex": case.patient_sex,
            "drug_route": case.drug_route,
            "drug_dose": case.drug_dose,
            "event_date": case.event_date,
            "event_outcome": case.event_outcome,
            "receipt_date": str(case.receipt_date) if case.receipt_date else None,
            "reporter_country": case.reporter_country,
            "is_serious": case.is_serious,
            # CIOMS-specific fields
            "patient_initials": case.patient_initials,
            "indication": case.indication,
            "therapy_start": case.therapy_start,
            "therapy_end": case.therapy_end,
            "therapy_duration": case.therapy_duration,
            "dechallenge": case.dechallenge,
            "rechallenge": case.rechallenge,
            "concomitant_drugs": case.concomitant_drugs,
            "medical_history": case.medical_history,
            "report_type": case.report_type,
            "reporter_email": case.reporter_email,
            "reporter_phone": case.reporter_phone,
            "manufacturer_name": case.manufacturer_name,
        },
        missing_fields=[
            {"field_name": mf.field_name, "criticality": mf.safety_criticality}
            for mf in case.missing_fields
        ],
        risk_score=0.0,
        response_probability=0.0,
        decision="PENDING",
        questions=[],
        reasoning="",
        messages=[],
        # Initialize required fields for connected orchestration
        decision_history=[],
        reporter_history=[],
        case_pattern_memory={},
        agent_confidences={},
        agent_reasonings={}
    )
    
    # Use connected orchestration for Feature-1 → Feature-2 → Feature-3 flow
    try:
        result = await smartfu_agent_connected(initial_state)
    except Exception as e:
        logger.warning(f"Connected orchestration failed, falling back: {e}")
        result = await smartfu_agent(initial_state)
    
    # AUTO FOLLOW-UP DISABLED — Manual trigger only via Novartis Review Dashboard
    if result.get("followup_required"):
        result["followup_triggered"] = False
        result["followup_note"] = "Follow-up ready but not sent. HA must manually trigger via Review Dashboard."
    
    return {
        "case_id": case_id,
        "analysis": result
    }
