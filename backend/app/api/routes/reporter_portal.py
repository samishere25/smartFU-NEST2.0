"""
Reporter Portal Routes - Secure token-based reporter response submission
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict
from datetime import datetime

from app.db.session import get_db
from app.models.case import AECase
from app.models.followup import FollowUpAttempt
from app.utils.secure_token_system import SecureTokenManager

router = APIRouter()
token_system = SecureTokenManager()


class ReporterSubmissionRequest(BaseModel):
    token: str
    responses: Dict[str, str]


@router.post("/submit-response")
async def submit_reporter_response(
    request: ReporterSubmissionRequest,
    db: Session = Depends(get_db)
):
    """
    Secure reporter portal submission endpoint.
    Validates token, updates case, logs submission, triggers re-analysis.
    """
    
    # Validate token
    token_data = token_system.validate_token(request.token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    case_id = token_data.get("case_id")
    
    # Get case
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Update case with reporter responses
    response_data = request.responses
    
    # Update missing fields if provided
    if "patient_sex" in response_data:
        case.patient_sex = response_data["patient_sex"]
    if "event_date" in response_data:
        case.event_date = response_data["event_date"]
    if "drug_dose" in response_data:
        case.drug_dose = response_data["drug_dose"]
    if "patient_age" in response_data:
        try:
            case.patient_age = int(response_data["patient_age"])
        except:
            pass
    
    # Create follow-up attempt record
    attempt = FollowUpAttempt(
        case_id=case_id,
        response_status="RESPONDED",
        response_data=response_data,
        contact_method="SECURE_PORTAL",
        responded_at=datetime.utcnow()
    )
    
    db.add(attempt)
    
    # Update case status
    case.case_status = "FOLLOWUP_RECEIVED"
    case.requires_followup = False
    
    # Mark case for re-analysis
    case.needs_reanalysis = True
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Thank you. Your information has been securely submitted and will help improve patient safety.",
        "case_updated": True,
        "reanalysis_queued": True
    }


@router.get("/validate-token/{token}")
async def validate_reporter_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate a reporter portal token and return case context.
    """
    
    token_data = token_system.validate_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    case_id = token_data.get("case_id")
    
    # Get case
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Build questions from missing fields
    questions = []
    for mf in case.missing_fields:
        question = {
            "field_name": mf.field_name,
            "question_text": f"What is the {mf.field_name.replace('_', ' ')}?",
            "criticality": mf.criticality if hasattr(mf, 'criticality') else "MEDIUM",
            "reason": f"This information is critical for safety assessment.",
            "field_type": "date" if "date" in mf.field_name.lower() else 
                         "select" if "sex" in mf.field_name.lower() else "text",
            "options": ["Male", "Female", "Unknown"] if "sex" in mf.field_name.lower() else None
        }
        questions.append(question)
    
    return {
        "valid": True,
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "suspect_drug": case.suspect_drug,
        "adverse_event": case.adverse_event,
        "questions": questions,
        "expires_at": token_data.get("exp")
    }
