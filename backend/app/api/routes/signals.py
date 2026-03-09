"""
Safety Signals Detection Routes
================================

All signal data is computed dynamically from the case database.
No hardcoded PRR values, no static signals.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.models.signal import SafetySignal
from app.models.case import AECase
from app.core.security import get_current_active_user
from app.services.pv_audit_service import PVAuditService

router = APIRouter()


# ─────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────

class SignalReviewRequest(BaseModel):
    action: str  # DOWNGRADE / ESCALATE / FALSE_POSITIVE / NOTE
    new_priority: Optional[str] = None  # CRITICAL/HIGH/MEDIUM/LOW
    note: str


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate_all_signals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk evaluate all drug-event combinations to detect/update signals."""
    from app.services.signal_service import bulk_evaluate_signals

    result = await bulk_evaluate_signals(db)
    return {
        "success": True,
        "message": "Signal evaluation completed",
        **result
    }


@router.get("/active")
async def get_active_signals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all active safety signals with dynamically computed metrics."""

    active_signals = db.query(SafetySignal).filter(
        SafetySignal.is_active == True,
        SafetySignal.signal_status.in_(['NEW', 'UNDER_REVIEW', 'ESCALATED'])
    ).order_by(SafetySignal.proportional_reporting_ratio.desc()).all()

    signals_data = []
    for signal in active_signals:
        # Use human-set priority if available, otherwise auto-calculate
        if signal.risk_priority:
            escalation_level = signal.risk_priority
        elif signal.prr is not None and signal.prr >= 8 and signal.trend == 'UP':
            escalation_level = 'CRITICAL'
        elif signal.prr is not None and signal.prr >= 5:
            escalation_level = 'HIGH'
        elif signal.prr is not None and signal.prr >= 3:
            escalation_level = 'MEDIUM'
        else:
            escalation_level = 'LOW'

        # Recommended actions based on escalation level
        recommended_actions = _get_recommended_actions(escalation_level)

        signals_data.append({
            'signal_id': str(signal.signal_id),
            'drug': signal.drug_name,
            'event': signal.adverse_event,
            'prr': float(signal.prr) if signal.prr else 0.0,
            'cases': signal.case_count or 0,
            'trend': signal.trend or 'STABLE',
            'seriousness_ratio': float(signal.seriousness_ratio) if signal.seriousness_ratio is not None else None,
            'escalation_level': escalation_level,
            'signal_status': signal.signal_status,
            'risk_priority': signal.risk_priority,
            'review_note': signal.review_note,
            'reviewed_by': signal.reviewed_by,
            'reviewed_at': signal.reviewed_at.isoformat() if signal.reviewed_at else None,
            'recommended_actions': recommended_actions,
            'detected_at': signal.detected_at.isoformat() if signal.detected_at else None,
            'last_updated': signal.updated_at.isoformat() if signal.updated_at else None,
        })

    # System status
    high_priority_count = sum(1 for s in signals_data if s['escalation_level'] in ['CRITICAL', 'HIGH'])
    if high_priority_count >= 3:
        system_status = 'CRITICAL'
    elif high_priority_count >= 1:
        system_status = 'ELEVATED'
    else:
        system_status = 'NORMAL'

    return {
        'system_status': system_status,
        'signals': signals_data,
        'total_signals': len(signals_data),
        'high_priority_count': high_priority_count,
        'last_updated': datetime.utcnow().isoformat()
    }


@router.post("/{signal_id}/escalate")
async def escalate_signal(
    signal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Initiate regulatory escalation process for a signal."""

    signal = _get_signal(db, signal_id)

    # Update signal status
    signal.signal_status = 'ESCALATED'
    signal.reviewed_at = datetime.utcnow()
    signal.reviewed_by = str(current_user.user_id)

    db.flush()

    # Audit trail
    PVAuditService.log_signal_reviewed(
        db,
        signal_id=signal.signal_id,
        actor_id=str(current_user.user_id),
        note="Signal escalated for regulatory review",
        action="ESCALATE",
    )
    db.commit()

    return {
        'status': 'success',
        'message': 'Regulatory escalation process initiated',
        'signal_id': signal_id,
        'escalated_at': signal.reviewed_at.isoformat(),
        'escalated_by': signal.reviewed_by,
    }


@router.post("/{signal_id}/review")
async def review_signal(
    signal_id: str,
    body: SignalReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Human oversight action on a signal.
    Supports: DOWNGRADE, ESCALATE, FALSE_POSITIVE, NOTE.
    All actions are audit-logged.
    """

    signal = _get_signal(db, signal_id)
    actor_id = str(current_user.user_id)
    old_priority = signal.risk_priority

    if body.action == "DOWNGRADE":
        if not body.new_priority:
            raise HTTPException(status_code=400, detail="new_priority required for DOWNGRADE")
        signal.risk_priority = body.new_priority
        signal.review_note = body.note
        signal.reviewed_by = actor_id
        signal.reviewed_at = datetime.utcnow()

        PVAuditService.log_signal_priority_changed(
            db, signal_id=signal.signal_id, actor_id=actor_id,
            old_priority=old_priority, new_priority=body.new_priority,
            reason=body.note,
        )

    elif body.action == "ESCALATE":
        signal.risk_priority = body.new_priority or "CRITICAL"
        signal.signal_status = "ESCALATED"
        signal.review_note = body.note
        signal.reviewed_by = actor_id
        signal.reviewed_at = datetime.utcnow()

        PVAuditService.log_signal_priority_changed(
            db, signal_id=signal.signal_id, actor_id=actor_id,
            old_priority=old_priority, new_priority=signal.risk_priority,
            reason=body.note,
        )

    elif body.action == "FALSE_POSITIVE":
        signal.signal_status = "FALSE_POSITIVE"
        signal.is_active = False
        signal.review_note = body.note
        signal.reviewed_by = actor_id
        signal.reviewed_at = datetime.utcnow()

        PVAuditService.log_signal_false_positive(
            db, signal_id=signal.signal_id, actor_id=actor_id,
            reason=body.note,
        )

    elif body.action == "NOTE":
        signal.review_note = body.note
        signal.reviewed_by = actor_id
        signal.reviewed_at = datetime.utcnow()

        PVAuditService.log_signal_reviewed(
            db, signal_id=signal.signal_id, actor_id=actor_id,
            note=body.note, action="NOTE",
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use DOWNGRADE/ESCALATE/FALSE_POSITIVE/NOTE")

    db.commit()

    return {
        'status': 'success',
        'action': body.action,
        'signal_id': signal_id,
        'risk_priority': signal.risk_priority,
        'signal_status': signal.signal_status,
        'reviewed_at': signal.reviewed_at.isoformat(),
    }


@router.get("/{signal_id}/cases")
async def get_signal_cases(
    signal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all cases related to a specific signal with risk distribution."""

    signal = _get_signal(db, signal_id)

    # Find related cases
    cases = db.query(AECase).filter(
        AECase.suspect_drug == signal.drug_name,
        AECase.adverse_event == signal.adverse_event,
    ).limit(200).all()

    # Risk distribution
    risk_dist = {}
    followup_status_dist = {}
    for c in cases:
        rl = c.risk_level or "UNKNOWN"
        risk_dist[rl] = risk_dist.get(rl, 0) + 1
        fs = c.followup_status or "UNKNOWN"
        followup_status_dist[fs] = followup_status_dist.get(fs, 0) + 1

    return {
        'signal_id': signal_id,
        'drug': signal.drug_name,
        'event': signal.adverse_event,
        'cases': [
            {
                'case_id': str(c.case_id),
                'primaryid': c.primaryid,
                'suspect_drug': c.suspect_drug,
                'adverse_event': c.adverse_event,
                'reporter_type': c.reporter_type,
                'is_serious': c.is_serious,
                'risk_level': c.risk_level,
                'followup_status': c.followup_status,
            }
            for c in cases
        ],
        'total_cases': len(cases),
        'risk_distribution': risk_dist,
        'followup_status_distribution': followup_status_dist,
    }


@router.get("/thresholds")
async def get_signal_thresholds(
    current_user: User = Depends(get_current_active_user)
):
    """Return current signal detection thresholds."""
    from app.services.signal_service import get_signal_thresholds
    return get_signal_thresholds()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_signal(db: Session, signal_id: str) -> SafetySignal:
    try:
        sig_uuid = UUID(signal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signal_id")

    signal = db.query(SafetySignal).filter(SafetySignal.signal_id == sig_uuid).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


def _get_recommended_actions(escalation_level: str) -> List[str]:
    if escalation_level == 'CRITICAL':
        return [
            'Notify FDA within 24 hours',
            'Prepare urgent safety communication',
            'Initiate immediate case review',
            'Alert medical safety team',
        ]
    elif escalation_level == 'HIGH':
        return [
            'Prepare regulatory submission within 72 hours',
            'Review all related cases',
            'Consult with medical affairs',
        ]
    elif escalation_level == 'MEDIUM':
        return [
            'Monitor trend closely',
            'Prepare safety assessment report',
            'Schedule safety committee review',
        ]
    return [
        'Continue routine monitoring',
        'Document in periodic safety report',
    ]
