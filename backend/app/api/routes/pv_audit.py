"""
PV Audit Trail Routes
======================

Provides read-only endpoints for the immutable pharmacovigilance audit trail.
Supports case-specific, signal-specific, and system-wide queries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.models.case import AECase
from app.core.security import get_current_active_user
from app.services.pv_audit_service import PVAuditService

router = APIRouter()


@router.get("/trail")
async def get_global_audit_trail(
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    actor_type: Optional[str] = Query(None, description="Filter by actor type (AI/HUMAN/SYSTEM/REPORTER)"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get system-wide audit trail with optional filters.
    Supports pagination via limit/offset.
    """
    entries = PVAuditService.get_global_audit_trail(
        db,
        action_type=action_type,
        actor_type=actor_type,
        limit=limit,
        offset=offset,
    )
    stats = PVAuditService.get_audit_stats(db)

    return {
        "entries": entries,
        "count": len(entries),
        "offset": offset,
        "limit": limit,
        "statistics": stats,
    }


@router.get("/trail/stats")
async def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get aggregate audit statistics."""
    return PVAuditService.get_audit_stats(db)


@router.get("/trail/case/{case_id}")
async def get_case_audit_trail(
    case_id: str,
    action_type: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get audit trail for a specific case (by UUID or primaryid).
    Returns chronological list of all audited actions.
    """
    # Resolve case
    case = _resolve_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    entries = PVAuditService.get_case_audit_trail(
        db,
        case_id=case.case_id,
        action_type=action_type,
        limit=limit,
        offset=offset,
    )

    return {
        "case_id": str(case.case_id),
        "primaryid": case.primaryid,
        "entries": entries,
        "count": len(entries),
    }


@router.get("/trail/signal/{signal_id}")
async def get_signal_audit_trail(
    signal_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get audit trail for a specific signal."""
    try:
        sig_uuid = UUID(signal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signal_id")

    entries = PVAuditService.get_signal_audit_trail(db, signal_id=sig_uuid, limit=limit)
    return {
        "signal_id": signal_id,
        "entries": entries,
        "count": len(entries),
    }


@router.get("/trail/action-types")
async def get_action_types(
    current_user: User = Depends(get_current_active_user),
):
    """Return all supported audit action types for filter UI."""
    return {
        "action_types": [
            "CASE_CREATED",
            "CIOMS_PARSED",
            "FIELDS_EXTRACTED",
            "AI_RISK_DECISION",
            "AI_FOLLOWUP_DECISION",
            "HUMAN_OVERRIDE",
            "FOLLOWUP_SENT",
            "RESPONSE_RECEIVED",
            "REVIEWER_NOTE_ADDED",
            "REGULATORY_ESCALATION",
            "SIGNAL_DETECTED",
            "SIGNAL_REVIEWED",
            "SIGNAL_PRIORITY_CHANGED",
            "SIGNAL_FALSE_POSITIVE",
            "LIFECYCLE_STAGE_CHANGE",
            "CASE_CLOSED",
            "REGULATORY_WORKFLOW_CREATED",
        ]
    }


def _resolve_case(db: Session, case_id: str):
    """Resolve case by primaryid or UUID."""
    try:
        return db.query(AECase).filter(AECase.primaryid == int(case_id)).first()
    except (ValueError, TypeError):
        pass
    try:
        return db.query(AECase).filter(AECase.case_id == UUID(case_id)).first()
    except (ValueError, TypeError):
        return None
