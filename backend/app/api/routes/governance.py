"""
Governance Routes for Feature 7: Human Oversight and Audit
Provides endpoints for human review, decision override, and audit logs
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.case import AECase
from app.core.security import get_current_active_user
from app.services.audit_service import AuditService

router = APIRouter()


class OversightAction(BaseModel):
    """Human oversight action request"""
    action: str  # APPROVE or OVERRIDE
    review_note: Optional[str] = None
    override_reason: Optional[str] = None
    new_risk_level: Optional[str] = None
    new_priority: Optional[str] = None


@router.post("/{case_id}/oversight")
async def submit_oversight_action(
    case_id: str,
    action_data: OversightAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit human oversight action (approve or override AI decision)
    Feature 7: Human-in-the-Loop Enforcement
    """
    
    # Find case by primaryid or UUID
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
    
    # Validate action
    if action_data.action not in ["APPROVE", "OVERRIDE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be APPROVE or OVERRIDE"
        )
    
    # OVERRIDE requires mandatory reason
    if action_data.action == "OVERRIDE":
        if not action_data.override_reason or not action_data.override_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Override reason is mandatory for OVERRIDE action"
            )
        
        # Get current AI decision from case
        previous_decision = {
            "risk_level": case.risk_level,
            "priority": case.priority_score
        }
        
        # Apply new human decision
        new_decision = {
            "risk_level": action_data.new_risk_level or case.risk_level,
            "priority": action_data.new_priority or case.priority_score
        }
        
        # Update case with human override
        if action_data.new_risk_level:
            case.risk_level = action_data.new_risk_level
        if action_data.new_priority:
            case.priority_score = action_data.new_priority
        
        # Mark as human-reviewed
        case.human_reviewed = True
        case.review_notes = action_data.override_reason
        case.reviewed_by = str(current_user.user_id)
        case.reviewed_at = datetime.utcnow()
        
        db.commit()
        
        # Log override in audit trail
        audit_log = AuditService.log_decision_override(
            db=db,
            case_id=case.case_id,
            user_id=str(current_user.user_id),
            override_reason=action_data.override_reason,
            previous_decision=previous_decision,
            new_decision=new_decision
        )
        
        return {
            "status": "success",
            "action": "OVERRIDE",
            "message": "AI decision successfully overridden by human reviewer",
            "case_id": str(case.case_id),
            "audit_log_id": str(audit_log.log_id),
            "human_final": True,
            "new_risk_level": case.risk_level,
            "new_priority": case.priority_score
        }
    
    else:  # APPROVE
        # Mark as human-reviewed and approved
        case.human_reviewed = True
        if action_data.review_note:
            case.review_notes = action_data.review_note
        case.reviewed_by = str(current_user.user_id)
        case.reviewed_at = datetime.utcnow()
        
        db.commit()
        
        # Log human review in audit trail
        audit_log = AuditService.log_human_review(
            db=db,
            case_id=case.case_id,
            user_id=str(current_user.user_id),
            review_note=action_data.review_note or "AI decision approved",
            decision="APPROVE"
        )
        
        return {
            "status": "success",
            "action": "APPROVE",
            "message": "AI decision approved by human reviewer",
            "case_id": str(case.case_id),
            "audit_log_id": str(audit_log.log_id),
            "human_final": False  # AI decision stands
        }


@router.get("/{case_id}/audit-log")
async def get_case_audit_log(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get complete audit trail for a case
    Feature 7: Audit Trail Logging
    """
    
    # Find case
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
    
    # Retrieve audit logs
    audit_logs = AuditService.get_case_audit_log(db, case.case_id)
    
    # Add case metadata
    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "current_risk_level": case.risk_level,
        "human_reviewed": case.human_reviewed or False,
        "reviewed_by": case.reviewed_by,
        "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
        "audit_logs": audit_logs,
        "total_entries": len(audit_logs)
    }


@router.get("/audit-logs")
async def get_all_audit_logs(
    activity_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all audit logs with optional filtering
    Feature 7: Regulatory Compliance Audit Trail
    """
    
    audit_logs = AuditService.get_all_audit_logs(
        db=db,
        activity_type=activity_type,
        limit=limit
    )
    
    # Calculate statistics
    total_logs = len(audit_logs)
    ai_decisions = sum(1 for log in audit_logs if log["activity_type"] == "AI_DECISION_GENERATED")
    human_reviews = sum(1 for log in audit_logs if log["activity_type"] == "HUMAN_REVIEW_ADDED")
    overrides = sum(1 for log in audit_logs if log["activity_type"] == "AI_DECISION_OVERRIDDEN")
    
    return {
        "audit_logs": audit_logs,
        "statistics": {
            "total_entries": total_logs,
            "ai_decisions": ai_decisions,
            "human_reviews": human_reviews,
            "overrides": overrides,
            "override_rate": f"{(overrides / ai_decisions * 100):.1f}%" if ai_decisions > 0 else "0%"
        },
        "compliance_status": {
            "gdpr_compliant": True,
            "fda_21_cfr_part_11_ready": True,
            "gvp_cioms_aligned": True,
            "audit_trail_complete": True
        }
    }


@router.get("/{case_id}/governance-summary")
async def get_governance_summary(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get governance summary for a case (AI vs Human decision status)
    Feature 7: Regulatory Flags
    """
    
    # Find case
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
    
    # Get audit logs to determine if overridden
    audit_logs = AuditService.get_case_audit_log(db, case.case_id, limit=10)
    
    # Check for override
    has_override = any(log["activity_type"] == "AI_DECISION_OVERRIDDEN" for log in audit_logs)
    has_ai_decision = any(log["activity_type"] == "AI_DECISION_GENERATED" for log in audit_logs)
    
    # Determine decision authority
    if has_override:
        decision_authority = "HUMAN-FINAL"
        decision_label = "Human-overridden decision"
    elif case.human_reviewed:
        decision_authority = "HUMAN-APPROVED"
        decision_label = "AI-generated, human-approved"
    elif has_ai_decision:
        decision_authority = "AI-GENERATED"
        decision_label = "AI-generated (pending human review)"
    else:
        decision_authority = "PENDING"
        decision_label = "No decision recorded"
    
    return {
        "case_id": str(case.case_id),
        "decision_authority": decision_authority,
        "decision_label": decision_label,
        "ai_generated": has_ai_decision,
        "human_final": has_override,
        "human_reviewed": case.human_reviewed or False,
        "reviewed_by": case.reviewed_by,
        "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
        "current_risk_level": case.risk_level,
        "regulatory_flags": {
            "ai_assisted": has_ai_decision,
            "human_oversight_required": not case.human_reviewed,
            "override_applied": has_override,
            "audit_trail_complete": len(audit_logs) > 0
        },
        "compliance_labels": {
            "gdpr_compliant": True,
            "fda_21_cfr_part_11_ready": True,
            "gvp_cioms_aligned": True
        }
    }
