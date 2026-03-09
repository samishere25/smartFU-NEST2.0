"""
API Endpoints for Adaptive Loop Analysis
Add these to your FastAPI router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid

from app.db.session import get_db
from app.models.case import AECase
from app.core.security import get_current_user
from app.models.user import User
from adaptive_loop_engine import run_adaptive_analysis

router = APIRouter()


@router.post("/cases/{case_id}/adaptive-analysis")
async def run_adaptive_case_analysis(
    case_id: uuid.UUID,
    simulate_responses: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Run adaptive loop analysis on a case
    
    Continuously iterates until safety confidence threshold is reached
    or maximum attempts is hit
    
    Args:
        case_id: Case to analyze
        simulate_responses: If True, simulates reporter responses (for demo)
    
    Returns:
        Complete analysis with iteration history
    """
    # Check case exists
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    
    # Run adaptive analysis
    try:
        result = await run_adaptive_analysis(
            case_id=str(case_id),
            db=db,
            simulate_responses=simulate_responses
        )
        
        return {
            "success": True,
            "case_id": str(case_id),
            "analysis": result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/cases/{case_id}/confidence-history")
async def get_confidence_history(
    case_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get confidence evolution history for a case
    
    Shows how confidence improved over iterations
    """
    # In production, would query CaseConfidenceHistory table
    # For now, return mock data
    
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    
    # Mock confidence history
    history = [
        {
            "iteration": 0,
            "timestamp": "2024-01-27T10:00:00",
            "overall_confidence": 0.45,
            "data_completeness": 0.40,
            "risk_assessment": 0.50,
            "trigger": "initial_analysis"
        },
        {
            "iteration": 1,
            "timestamp": "2024-01-27T10:15:00",
            "overall_confidence": 0.67,
            "data_completeness": 0.70,
            "risk_assessment": 0.65,
            "trigger": "response_received",
            "information_gain": 0.22
        },
        {
            "iteration": 2,
            "timestamp": "2024-01-27T10:30:00",
            "overall_confidence": 0.87,
            "data_completeness": 0.90,
            "risk_assessment": 0.85,
            "trigger": "response_received",
            "information_gain": 0.20
        }
    ]
    
    return {
        "case_id": str(case_id),
        "history": history,
        "final_confidence": 0.87,
        "converged": True,
        "convergence_reason": "CONFIDENCE_THRESHOLD_REACHED"
    }


@router.get("/cases/{case_id}/followup-attempts")
async def get_followup_attempts(
    case_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all follow-up attempts for a case
    
    Shows complete lifecycle of follow-up efforts
    """
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    
    # In production, would query FollowUpAttempt table
    # Mock data for now
    attempts = [
        {
            "attempt_id": str(uuid.uuid4()),
            "iteration_number": 1,
            "sent_at": "2024-01-27T10:05:00",
            "status": "RESPONDED",
            "response_received_at": "2024-01-27T10:15:00",
            "response_time_hours": 0.17,
            "questions_sent": 3,
            "questions_answered": 2,
            "information_gained": 0.22,
            "safety_confidence_before": 0.45,
            "safety_confidence_after": 0.67
        },
        {
            "attempt_id": str(uuid.uuid4()),
            "iteration_number": 2,
            "sent_at": "2024-01-27T10:20:00",
            "status": "RESPONDED",
            "response_received_at": "2024-01-27T10:30:00",
            "response_time_hours": 0.17,
            "questions_sent": 2,
            "questions_answered": 2,
            "information_gained": 0.20,
            "safety_confidence_before": 0.67,
            "safety_confidence_after": 0.87
        }
    ]
    
    return {
        "case_id": str(case_id),
        "total_attempts": len(attempts),
        "successful_responses": 2,
        "response_rate": 1.0,
        "total_confidence_gain": 0.42,
        "attempts": attempts
    }


@router.get("/cases/{case_id}/adaptive-session")
async def get_adaptive_session(
    case_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the complete adaptive loop session for a case
    
    Shows end-to-end journey from initial analysis to convergence
    """
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    
    # Mock session data
    session = {
        "session_id": str(uuid.uuid4()),
        "case_id": str(case_id),
        "started_at": "2024-01-27T10:00:00",
        "completed_at": "2024-01-27T10:30:00",
        "duration_minutes": 30,
        "initial_state": {
            "confidence": 0.45,
            "completeness": 0.40,
            "missing_fields": 5
        },
        "final_state": {
            "confidence": 0.87,
            "completeness": 0.90,
            "missing_fields": 1
        },
        "iterations": 2,
        "questions_sent": 5,
        "responses_received": 4,
        "response_rate": 0.80,
        "converged": True,
        "convergence_reason": "CONFIDENCE_THRESHOLD_REACHED",
        "efficiency_rating": "EXCELLENT",
        "confidence_gain": 0.42,
        "gain_per_iteration": 0.21
    }
    
    return session


# Add these to your main router
"""
In app/api/routes/__init__.py or app/main.py:

from .adaptive_routes import router as adaptive_router

app.include_router(
    adaptive_router,
    prefix="/api",
    tags=["adaptive-analysis"]
)
"""
