"""
Follow-Up Lifecycle Tracking API Routes (Production)
=====================================================

Feature-4: Production-ready lifecycle tracking with database persistence.

All data is persisted to PostgreSQL via SQLAlchemy.
NO in-memory storage.

Endpoints:
- POST /lifecycle/init - Initialize lifecycle for a case
- GET /lifecycle/{case_id} - Get lifecycle status
- POST /lifecycle/{case_id}/followup-sent - Record follow-up sent
- POST /lifecycle/{case_id}/response - Record response received
- POST /lifecycle/{case_id}/check-reminder - Check if reminder due
- POST /lifecycle/{case_id}/send-reminder - Record reminder sent
- POST /lifecycle/{case_id}/check-escalation - Check if escalation needed
- POST /lifecycle/{case_id}/escalate - Trigger escalation
- POST /lifecycle/{case_id}/check-dead-case - Check dead case status
- POST /lifecycle/{case_id}/dead-case - Mark as dead case
- GET /lifecycle/{case_id}/audit - Get audit log
- GET /lifecycle/policies/list - List available policies
- GET /lifecycle/stats/overview - Get lifecycle statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging
import uuid

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.services.lifecycle_db_service import LifecycleDBService
from app.services.lifecycle_tracker import HCP_POLICY, NON_HCP_POLICY
from app.models import AECase

router = APIRouter(
    prefix="/lifecycle",
    tags=["Lifecycle Tracking"],
    dependencies=[Depends(get_current_active_user)]
)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER: Resolve case_id from UUID or primary_id
# ============================================================================

def resolve_case_id(case_id_or_primary: str, db: Session) -> str:
    """
    Resolve case_id - accepts both UUID format and primaryid.
    
    If input looks like a UUID, use it directly.
    Otherwise, look up by primaryid in ae_cases table.
    """
    # Check if it's a valid UUID
    try:
        uuid.UUID(case_id_or_primary)
        return case_id_or_primary  # It's already a valid UUID
    except ValueError:
        pass
    
    # Not a UUID - try to look up by primaryid (integer)
    try:
        primary_id_int = int(case_id_or_primary)
        case = db.query(AECase).filter(AECase.primaryid == primary_id_int).first()
        
        if case:
            logger.info(f"Resolved primaryid {case_id_or_primary} to UUID {case.case_id}")
            return str(case.case_id)
    except ValueError:
        pass
    
    # Not found by primaryid either
    raise HTTPException(
        status_code=404, 
        detail=f"Case not found: '{case_id_or_primary}'. Use UUID case_id or valid primaryid."
    )


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class InitLifecycleRequest(BaseModel):
    """Request to initialize lifecycle"""
    case_id: str
    reporter_type: str = Field(..., description="MD/HP/PT/CN etc")
    seriousness_level: str = Field(default="medium", description="low/medium/high/critical")
    initial_completeness: float = Field(default=0.0, ge=0.0, le=1.0)


class FollowUpSentRequest(BaseModel):
    """Request to record follow-up sent"""
    questions_sent: List[Dict[str, Any]]
    channel: str = Field(..., description="EMAIL/WHATSAPP/PHONE/SMS")
    sent_to: Optional[str] = None


class ResponseReceivedRequest(BaseModel):
    """Request to record response received"""
    questions_answered: int = Field(..., ge=0)
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    safety_confidence: float = Field(..., ge=0.0, le=1.0)
    is_complete: bool = False


class EscalationRequest(BaseModel):
    """Request to trigger escalation"""
    reason: str
    escalate_to: str = Field(default="supervisor")


class DeadCaseRequest(BaseModel):
    """Request to mark dead case"""
    reason: str
    closed_by: str = Field(default="system")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/init", response_model=Dict[str, Any])
async def initialize_lifecycle(
    request: InitLifecycleRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize lifecycle tracking for a case.
    
    Creates a new lifecycle record in the database.
    Called when Feature-1 determines follow-up is required.
    """
    try:
        service = LifecycleDBService(db)
        
        lifecycle = service.initialize_lifecycle(
            case_id=request.case_id,
            reporter_type=request.reporter_type,
            seriousness_level=request.seriousness_level,
            initial_completeness=request.initial_completeness
        )
        
        logger.info(f"✅ Lifecycle initialized for case {request.case_id}")
        
        return {
            "success": True,
            "message": "Lifecycle initialized",
            "lifecycle": service.get_lifecycle_summary(lifecycle)
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize lifecycle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}", response_model=Dict[str, Any])
async def get_lifecycle_status(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Get lifecycle status for a case from database.
    Accepts both UUID case_id or primary_id.
    """
    # Resolve case_id (supports UUID or primary_id)
    resolved_case_id = resolve_case_id(case_id, db)
    
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        # Return initial/empty lifecycle status instead of 404
        # Lifecycle may not be initialized until case is analyzed
        return {
            "success": True,
            "lifecycle": {
                "case_id": case_id,
                "status": "NOT_INITIALIZED",
                "attempt_count": 0,
                "max_attempts": 3,
                "current_phase": "pending",
                "deadline_met": None,
                "days_remaining": None,
                "message": "Lifecycle not yet initialized. Analyze the case to auto-initialize lifecycle tracking."
            },
            "summary": {
                "status": "NOT_INITIALIZED",
                "attempt_count": 0,
                "completeness_current": 0.0
            }
        }
    
    # Update deadline awareness
    lifecycle = service.update_deadline_awareness(lifecycle)
    
    return {
        "success": True,
        "lifecycle": service.lifecycle_to_dict(lifecycle),
        "summary": service.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/followup-sent", response_model=Dict[str, Any])
async def record_followup_sent(
    case_id: str,
    request: FollowUpSentRequest,
    db: Session = Depends(get_db)
):
    """
    Record that a follow-up was sent.
    Creates attempt record in database.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    lifecycle = service.record_followup_sent(
        lifecycle=lifecycle,
        questions_sent=request.questions_sent,
        channel=request.channel,
        sent_to=request.sent_to
    )
    
    return {
        "success": True,
        "message": f"Follow-up #{lifecycle.attempt_count} recorded",
        "summary": service.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/response", response_model=Dict[str, Any])
async def record_response_received(
    case_id: str,
    request: ResponseReceivedRequest,
    db: Session = Depends(get_db)
):
    """
    Record that a response was received from reporter.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    lifecycle = service.record_response_received(
        lifecycle=lifecycle,
        questions_answered=request.questions_answered,
        completeness_score=request.completeness_score,
        safety_confidence=request.safety_confidence,
        is_complete=request.is_complete
    )
    
    # Auto-close if complete
    if lifecycle.response_status == "complete":
        lifecycle = service.close_case_success(lifecycle)
    
    return {
        "success": True,
        "message": f"Response recorded: {lifecycle.response_status}",
        "summary": service.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/check-reminder", response_model=Dict[str, Any])
async def check_reminder_due(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a reminder should be sent (24-hour compliance rule).
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    is_due, reason = service.is_reminder_due(lifecycle)
    
    return {
        "success": True,
        "is_reminder_due": is_due,
        "reason": reason,
        "next_reminder_due": lifecycle.next_reminder_due.isoformat() if lifecycle.next_reminder_due else None
    }


@router.post("/{case_id}/send-reminder", response_model=Dict[str, Any])
async def send_reminder(
    case_id: str,
    channel: str = Query(default="EMAIL"),
    db: Session = Depends(get_db)
):
    """
    Record that a reminder was sent.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    is_due, reason = service.is_reminder_due(lifecycle)
    
    if not is_due:
        return {
            "success": False,
            "message": f"Reminder not due: {reason}",
            "summary": service.get_lifecycle_summary(lifecycle)
        }
    
    lifecycle = service.record_reminder_sent(lifecycle, channel)
    
    return {
        "success": True,
        "message": f"Reminder #{lifecycle.attempt_count} sent",
        "summary": service.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/check-escalation", response_model=Dict[str, Any])
async def check_escalation_needed(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if escalation is needed.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    needs_escalation, reason, escalate_to = service.check_escalation_needed(lifecycle)
    
    return {
        "success": True,
        "needs_escalation": needs_escalation,
        "reason": reason,
        "escalate_to": escalate_to,
        "current_status": lifecycle.escalation_status
    }


@router.post("/{case_id}/escalate", response_model=Dict[str, Any])
async def trigger_escalation(
    case_id: str,
    request: EscalationRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger escalation for a case.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    lifecycle = service.trigger_escalation(
        lifecycle=lifecycle,
        reason=request.reason,
        escalate_to=request.escalate_to
    )
    
    return {
        "success": True,
        "message": f"Case escalated to {request.escalate_to}",
        "summary": service.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/check-dead-case", response_model=Dict[str, Any])
async def check_dead_case(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if case should be marked as dead.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    is_dead, reason = service.check_dead_case(lifecycle)
    
    return {
        "success": True,
        "is_dead_case": is_dead,
        "reason": reason,
        "current_status": lifecycle.lifecycle_status
    }


@router.post("/{case_id}/dead-case", response_model=Dict[str, Any])
async def mark_dead_case(
    case_id: str,
    request: DeadCaseRequest,
    db: Session = Depends(get_db)
):
    """
    Mark case as dead.
    
    This is POLICY-CONTROLLED - AI cannot override.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}. Initialize lifecycle first.")
    
    # Verify dead case is allowed
    is_dead, reason = service.check_dead_case(lifecycle)
    
    if not is_dead:
        return {
            "success": False,
            "message": f"Cannot mark as dead: {reason}",
            "summary": service.get_lifecycle_summary(lifecycle)
        }
    
    lifecycle = service.mark_dead_case(
        lifecycle=lifecycle,
        reason=request.reason,
        closed_by=request.closed_by
    )
    
    return {
        "success": True,
        "message": "Case marked as dead",
        "summary": service.get_lifecycle_summary(lifecycle)
    }


@router.get("/{case_id}/audit", response_model=Dict[str, Any])
async def get_audit_log(
    case_id: str,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db)
):
    """
    Get audit log for a case from database.
    
    Full compliance trail.
    """
    resolved_case_id = resolve_case_id(case_id, db)
    service = LifecycleDBService(db)
    lifecycle = service.get_lifecycle_by_case_id(resolved_case_id)
    
    if not lifecycle:
        # Return empty audit log instead of 404
        return {
            "success": True,
            "case_id": case_id,
            "total_entries": 0,
            "audit_log": [],
            "message": "Lifecycle not yet initialized. No audit entries."
        }
    
    audit_logs = service.get_audit_log(str(lifecycle.lifecycle_id), limit)
    
    return {
        "success": True,
        "case_id": case_id,
        "total_entries": len(audit_logs),
        "audit_log": [service._audit_to_dict(log) for log in audit_logs]
    }


@router.get("/policies/list", response_model=Dict[str, Any])
async def list_policies():
    """
    List available policies.
    """
    return {
        "success": True,
        "policies": {
            "HCP_POLICY": {
                "reporter_type": HCP_POLICY.reporter_type,
                "max_attempts": HCP_POLICY.max_attempts,
                "reminder_interval_hours": HCP_POLICY.reminder_interval_hours,
                "questions_per_round": HCP_POLICY.questions_per_round,
                "escalation_after_attempts": HCP_POLICY.escalation_after_attempts,
                "escalate_to": HCP_POLICY.escalate_to,
                "allow_auto_dead_case": HCP_POLICY.allow_auto_dead_case
            },
            "NON_HCP_POLICY": {
                "reporter_type": NON_HCP_POLICY.reporter_type,
                "max_attempts": NON_HCP_POLICY.max_attempts,
                "reminder_interval_hours": NON_HCP_POLICY.reminder_interval_hours,
                "questions_per_round": NON_HCP_POLICY.questions_per_round,
                "escalation_after_attempts": NON_HCP_POLICY.escalation_after_attempts,
                "escalate_to": NON_HCP_POLICY.escalate_to,
                "allow_auto_dead_case": NON_HCP_POLICY.allow_auto_dead_case
            }
        }
    }


@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_lifecycle_stats_overview(
    db: Session = Depends(get_db)
):
    """
    Get overview stats for all tracked lifecycles from database.
    """
    service = LifecycleDBService(db)
    stats = service.get_lifecycle_stats()
    
    return {
        "success": True,
        **stats
    }
