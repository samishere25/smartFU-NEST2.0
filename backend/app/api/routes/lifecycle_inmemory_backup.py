"""
Follow-Up Lifecycle Tracking API Routes
========================================

Feature-4: Lifecycle tracking endpoints.

Endpoints:
- POST /lifecycle/init - Initialize lifecycle for a case
- GET /lifecycle/{case_id} - Get lifecycle status
- POST /lifecycle/{case_id}/followup-sent - Record follow-up sent
- POST /lifecycle/{case_id}/response - Record response received
- POST /lifecycle/{case_id}/check-reminder - Check if reminder due
- POST /lifecycle/{case_id}/escalate - Trigger escalation
- POST /lifecycle/{case_id}/dead-case - Mark as dead case
- GET /lifecycle/{case_id}/audit - Get audit log
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from app.db.session import get_db
from app.services.lifecycle_tracker import (
    FollowUpLifecycleTracker,
    get_policy,
    HCP_POLICY,
    NON_HCP_POLICY
)
from app.models.case import AECase

router = APIRouter(prefix="/lifecycle", tags=["Lifecycle Tracking"])
logger = logging.getLogger(__name__)

# In-memory storage for demo (in production, use DB)
# This would be replaced with actual DB queries
_lifecycle_store: Dict[str, Dict] = {}


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


class LifecycleSummary(BaseModel):
    """Lifecycle summary response"""
    case_id: str
    reporter_type: str
    lifecycle_status: str
    attempt_count: int
    max_attempts: int
    response_status: str
    escalation_status: str
    days_remaining: Optional[int]
    completeness_score: float
    dead_case_flag: bool
    policy_applied: str
    next_action: str


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
    
    Called when Feature-1 determines follow-up is required.
    """
    try:
        tracker = FollowUpLifecycleTracker(db)
        
        lifecycle = tracker.initialize_lifecycle(
            case_id=request.case_id,
            reporter_type=request.reporter_type,
            seriousness_level=request.seriousness_level,
            initial_completeness=request.initial_completeness
        )
        
        # Store in memory (replace with DB in production)
        _lifecycle_store[request.case_id] = lifecycle
        
        logger.info(f"✅ Lifecycle initialized for case {request.case_id}")
        
        return {
            "success": True,
            "message": "Lifecycle initialized",
            "lifecycle": tracker.get_lifecycle_summary(lifecycle)
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
    Get lifecycle status for a case.
    """
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    # Update deadline awareness
    lifecycle = tracker.update_deadline_awareness(lifecycle)
    _lifecycle_store[case_id] = lifecycle
    
    return {
        "success": True,
        "lifecycle": lifecycle,
        "summary": tracker.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/followup-sent", response_model=Dict[str, Any])
async def record_followup_sent(
    case_id: str,
    request: FollowUpSentRequest,
    db: Session = Depends(get_db)
):
    """
    Record that a follow-up was sent.
    """
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    lifecycle = tracker.record_followup_sent(
        lifecycle=lifecycle,
        questions_sent=request.questions_sent,
        channel=request.channel,
        sent_to=request.sent_to
    )
    
    _lifecycle_store[case_id] = lifecycle
    
    return {
        "success": True,
        "message": f"Follow-up #{lifecycle['attempt_count']} recorded",
        "summary": tracker.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/response", response_model=Dict[str, Any])
async def record_response_received(
    case_id: str,
    request: ResponseReceivedRequest,
    db: Session = Depends(get_db)
):
    """
    Record that a response was received.
    """
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    lifecycle = tracker.record_response_received(
        lifecycle=lifecycle,
        questions_answered=request.questions_answered,
        completeness_score=request.completeness_score,
        safety_confidence=request.safety_confidence,
        is_complete=request.is_complete
    )
    
    _lifecycle_store[case_id] = lifecycle
    
    # Check if case should be closed
    if lifecycle.get("response_status") == "complete":
        lifecycle = tracker.close_case_success(lifecycle)
        _lifecycle_store[case_id] = lifecycle
    
    return {
        "success": True,
        "message": f"Response recorded: {lifecycle['response_status']}",
        "summary": tracker.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/check-reminder", response_model=Dict[str, Any])
async def check_reminder_due(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a reminder should be sent.
    
    Implements 24-hour compliance rule.
    """
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    is_due, reason = tracker.is_reminder_due(lifecycle)
    
    return {
        "success": True,
        "is_reminder_due": is_due,
        "reason": reason,
        "next_reminder_due": lifecycle.get("next_reminder_due")
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
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    # Check if reminder is actually due
    is_due, reason = tracker.is_reminder_due(lifecycle)
    
    if not is_due:
        return {
            "success": False,
            "message": f"Reminder not due: {reason}",
            "summary": tracker.get_lifecycle_summary(lifecycle)
        }
    
    lifecycle = tracker.record_reminder_sent(lifecycle, channel)
    _lifecycle_store[case_id] = lifecycle
    
    return {
        "success": True,
        "message": f"Reminder #{lifecycle['attempt_count']} sent",
        "summary": tracker.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/check-escalation", response_model=Dict[str, Any])
async def check_escalation_needed(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if escalation is needed.
    """
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    needs_escalation, reason, escalate_to = tracker.check_escalation_needed(lifecycle)
    
    return {
        "success": True,
        "needs_escalation": needs_escalation,
        "reason": reason,
        "escalate_to": escalate_to,
        "current_status": lifecycle.get("escalation_status")
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
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    lifecycle = tracker.trigger_escalation(
        lifecycle=lifecycle,
        reason=request.reason,
        escalate_to=request.escalate_to
    )
    
    _lifecycle_store[case_id] = lifecycle
    
    return {
        "success": True,
        "message": f"Case escalated to {request.escalate_to}",
        "summary": tracker.get_lifecycle_summary(lifecycle)
    }


@router.post("/{case_id}/check-dead-case", response_model=Dict[str, Any])
async def check_dead_case(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if case should be marked as dead.
    """
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    is_dead, reason = tracker.check_dead_case(lifecycle)
    
    return {
        "success": True,
        "is_dead_case": is_dead,
        "reason": reason,
        "current_status": lifecycle.get("lifecycle_status")
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
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    tracker = FollowUpLifecycleTracker(db)
    
    # Verify dead case is allowed
    is_dead, reason = tracker.check_dead_case(lifecycle)
    
    if not is_dead:
        return {
            "success": False,
            "message": f"Cannot mark as dead: {reason}",
            "summary": tracker.get_lifecycle_summary(lifecycle)
        }
    
    lifecycle = tracker.mark_dead_case(
        lifecycle=lifecycle,
        reason=request.reason,
        closed_by=request.closed_by
    )
    
    _lifecycle_store[case_id] = lifecycle
    
    return {
        "success": True,
        "message": "Case marked as dead",
        "summary": tracker.get_lifecycle_summary(lifecycle)
    }


@router.get("/{case_id}/audit", response_model=Dict[str, Any])
async def get_audit_log(
    case_id: str,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db)
):
    """
    Get audit log for a case.
    
    Full compliance trail.
    """
    lifecycle = _lifecycle_store.get(case_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"Lifecycle not found for case {case_id}")
    
    audit_log = lifecycle.get("audit_log", [])
    
    # Return most recent entries
    recent_entries = audit_log[-limit:] if len(audit_log) > limit else audit_log
    
    return {
        "success": True,
        "case_id": case_id,
        "total_entries": len(audit_log),
        "returned_entries": len(recent_entries),
        "audit_log": recent_entries
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
async def get_lifecycle_stats():
    """
    Get overview stats for all tracked lifecycles.
    """
    total = len(_lifecycle_store)
    
    if total == 0:
        return {
            "success": True,
            "total_cases": 0,
            "by_status": {},
            "by_reporter_type": {},
            "escalated_count": 0,
            "dead_case_count": 0
        }
    
    # Count by status
    by_status = {}
    by_reporter = {}
    escalated = 0
    dead_cases = 0
    
    for lifecycle in _lifecycle_store.values():
        status = lifecycle.get("lifecycle_status", "unknown")
        reporter = lifecycle.get("reporter_type", "unknown")
        
        by_status[status] = by_status.get(status, 0) + 1
        by_reporter[reporter] = by_reporter.get(reporter, 0) + 1
        
        if lifecycle.get("escalation_status") not in ["none", None]:
            escalated += 1
        
        if lifecycle.get("dead_case_flag"):
            dead_cases += 1
    
    return {
        "success": True,
        "total_cases": total,
        "by_status": by_status,
        "by_reporter_type": by_reporter,
        "escalated_count": escalated,
        "dead_case_count": dead_cases
    }
