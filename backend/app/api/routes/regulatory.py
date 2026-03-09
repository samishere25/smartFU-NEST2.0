"""
Regulatory Workflow Routes
POST /api/regulatory/start — trigger workflow for signal escalation

Creates real workflow, freezes signal snapshot, logs to audit trail.
No auto-send — requires human confirmation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import logging

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.signal import SafetySignal
from app.models.regulatory import RegulatoryWorkflow
from app.schemas.regulatory import RegulatoryStartRequest, RegulatoryWorkflowResponse
from app.services.pv_audit_service import PVAuditService

logger = logging.getLogger(__name__)

router = APIRouter()


def _due_date_for_signal(signal: SafetySignal) -> datetime:
    """Calculate due date based on signal strength / seriousness."""
    if signal.signal_strength == "STRONG":
        return datetime.utcnow() + timedelta(days=7)
    if signal.signal_strength == "MODERATE":
        return datetime.utcnow() + timedelta(days=15)
    return datetime.utcnow() + timedelta(days=30)


def _build_signal_snapshot(signal: SafetySignal) -> dict:
    """Build a frozen snapshot of the signal at the moment of regulatory escalation."""
    return {
        "signal_id": str(signal.signal_id),
        "drug_name": signal.drug_name,
        "adverse_event": signal.adverse_event,
        "signal_type": signal.signal_type,
        "signal_strength": signal.signal_strength,
        "case_count": signal.case_count,
        "prr": float(signal.proportional_reporting_ratio) if signal.proportional_reporting_ratio else None,
        "seriousness_ratio": float(signal.seriousness_ratio) if signal.seriousness_ratio else None,
        "trend": signal.trend,
        "risk_priority": signal.risk_priority,
        "signal_status": signal.signal_status,
        "detected_at": signal.detected_at.isoformat() if signal.detected_at else None,
        "snapshot_taken_at": datetime.utcnow().isoformat(),
    }


@router.post("/start", response_model=RegulatoryWorkflowResponse)
def start_regulatory_workflow(
    body: RegulatoryStartRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Start a regulatory workflow for a given signal.
    - Freezes signal snapshot (audit logged)
    - Changes signal status to UNDER_REVIEW
    - Creates regulatory workflow instance
    - Idempotent — returns existing workflow if one already exists
    """

    # Validate signal_id UUID
    try:
        signal_uuid = uuid.UUID(body.signalId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="signalId must be a valid UUID",
        )

    # Check signal exists
    signal = db.query(SafetySignal).filter(SafetySignal.signal_id == signal_uuid).first()
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal {body.signalId} not found",
        )

    # Idempotency: return existing workflow
    existing = (
        db.query(RegulatoryWorkflow)
        .filter(RegulatoryWorkflow.signal_id == signal_uuid)
        .first()
    )
    if existing:
        logger.info("Returning existing regulatory workflow %s for signal %s", existing.id, body.signalId)
        return _to_response(existing)

    # ── Freeze signal snapshot ──
    snapshot = _build_signal_snapshot(signal)
    signal.frozen_snapshot = snapshot
    signal.signal_status = "UNDER_REVIEW"
    signal.reviewed_at = datetime.utcnow()
    signal.reviewed_by = str(current_user.user_id) if hasattr(current_user, 'user_id') else "system"

    # ── Create regulatory workflow ──
    workflow = RegulatoryWorkflow(
        id=uuid.uuid4(),
        signal_id=signal_uuid,
        status="IN_PROGRESS",
        report_type="CIOMS_DRAFT",
        due_date=_due_date_for_signal(signal),
        cioms_placeholder=f"CIOMS I draft for signal {body.signalId}",
        created_at=datetime.utcnow(),
    )
    db.add(workflow)
    db.flush()

    # ── Audit trail: regulatory escalation ──
    actor_id = str(current_user.user_id) if hasattr(current_user, 'user_id') else "system"
    PVAuditService.log_regulatory_escalation(
        db,
        signal_id=signal_uuid,
        actor_id=actor_id,
        workflow_id=workflow.id,
        snapshot=snapshot,
    )
    PVAuditService.log_regulatory_workflow_created(
        db,
        signal_id=signal_uuid,
        workflow_id=workflow.id,
        actor_id=actor_id,
        due_date=workflow.due_date.isoformat(),
    )

    # ── Governance audit trail: REGULATORY_PROCESS_STARTED ──
    try:
        from app.services.audit_service import AuditService
        AuditService.log_regulatory_process_started(
            db,
            signal_id=signal_uuid,
            workflow_id=workflow.id,
            user_id=actor_id,
            due_date=workflow.due_date.isoformat() if workflow.due_date else None,
        )
    except Exception:
        pass  # Don't fail workflow creation if audit logging fails

    db.commit()
    db.refresh(workflow)

    logger.info("Created regulatory workflow %s for signal %s", workflow.id, body.signalId)
    return _to_response(workflow)


def _to_response(wf: RegulatoryWorkflow) -> RegulatoryWorkflowResponse:
    return RegulatoryWorkflowResponse(
        id=str(wf.id),
        signal_id=str(wf.signal_id),
        status=wf.status,
        report_type=wf.report_type,
        due_date=wf.due_date,
        created_at=wf.created_at,
    )
