"""
Signal Evaluation Service
Evaluates and updates safety signals based on real case data in the database.

All PRR values, seriousness ratios, and trends are computed dynamically.
No hardcoded signal data.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case as sql_case
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.models.signal import SafetySignal
from app.models.case import AECase

# ─────────────────────────────────────────────────
# CONFIGURABLE THRESHOLDS (can be moved to DB/env)
# ─────────────────────────────────────────────────

SIGNAL_THRESHOLDS = {
    "min_case_count": 2,              # Minimum cases to create a signal
    "prr_threshold": 2.0,             # Minimum PRR to consider a signal
    "prr_strong": 8.0,                # PRR for STRONG signal
    "prr_moderate": 3.0,              # PRR for MODERATE signal
    "case_count_strong": 5,           # Minimum cases for STRONG
    "case_count_moderate": 3,         # Minimum cases for MODERATE
    "seriousness_ratio_alert": 0.5,   # Seriousness ratio that triggers alert
    "trend_recent_window_days": 7,    # Window for trend calculation
    "trend_up_threshold": 0.3,        # 30% of cases in recent window = UP
    "trend_down_threshold": 0.1,      # Less than 10% = DOWN
}


async def evaluate_signals_for_case(case: AECase, db: Session) -> Dict[str, Any]:
    """
    Evaluate safety signals when a case is created or updated.
    Computes all metrics dynamically from the database.
    """

    drug = case.suspect_drug
    event = case.adverse_event

    if not drug or not event:
        return {"signals_updated": 0, "new_signals": 0}

    thresholds = SIGNAL_THRESHOLDS

    # Check if signal already exists for this drug-event combination
    existing_signal = db.query(SafetySignal).filter(
        and_(
            SafetySignal.drug_name == drug,
            SafetySignal.adverse_event == event
        )
    ).first()

    # ── Count cases for PRR calculation ──
    # a = cases with drug AND event
    a = db.query(func.count(AECase.case_id)).filter(
        and_(AECase.suspect_drug == drug, AECase.adverse_event == event)
    ).scalar() or 0

    # b = cases with drug (any event)
    b = db.query(func.count(AECase.case_id)).filter(
        AECase.suspect_drug == drug
    ).scalar() or 1

    # c = cases with event (any drug)
    c = db.query(func.count(AECase.case_id)).filter(
        AECase.adverse_event == event
    ).scalar() or 1

    # d = total cases in database
    d = db.query(func.count(AECase.case_id)).scalar() or 1

    # ── Proportional Reporting Ratio ──
    prr = (a / b) / (c / d) if b > 0 and c > 0 and d > 0 else 0.0

    # ── Seriousness ratio (from actual case data) ──
    serious_count = db.query(func.count(AECase.case_id)).filter(
        and_(
            AECase.suspect_drug == drug,
            AECase.adverse_event == event,
            AECase.is_serious == True
        )
    ).scalar() or 0
    seriousness_ratio = serious_count / a if a > 0 else 0.0

    # ── Signal strength ──
    if prr >= thresholds["prr_strong"] and a >= thresholds["case_count_strong"]:
        signal_strength = "STRONG"
        signal_type = "CONFIRMED"
    elif prr >= thresholds["prr_moderate"] and a >= thresholds["case_count_moderate"]:
        signal_strength = "MODERATE"
        signal_type = "EMERGING"
    elif prr >= thresholds["prr_threshold"]:
        signal_strength = "WEAK"
        signal_type = "EMERGING"
    else:
        signal_strength = "MINIMAL"
        signal_type = "DISMISSED"

    # ── Trend calculation (rolling window) ──
    window_start = datetime.utcnow() - timedelta(days=thresholds["trend_recent_window_days"])
    recent_cases = db.query(func.count(AECase.case_id)).filter(
        and_(
            AECase.suspect_drug == drug,
            AECase.adverse_event == event,
            AECase.created_at >= window_start
        )
    ).scalar() or 0

    if a > 0 and recent_cases >= a * thresholds["trend_up_threshold"]:
        trend = "UP"
    elif a > 0 and recent_cases <= a * thresholds["trend_down_threshold"]:
        trend = "DOWN"
    else:
        trend = "STABLE"

    # ── Risk priority (auto-calculated, can be overridden by human) ──
    if prr >= thresholds["prr_strong"] and trend == "UP":
        auto_priority = "CRITICAL"
    elif prr >= thresholds["prr_strong"]:
        auto_priority = "HIGH"
    elif prr >= thresholds["prr_moderate"]:
        auto_priority = "MEDIUM"
    else:
        auto_priority = "LOW"

    result = {"signals_updated": 0, "new_signals": 0}

    if existing_signal:
        # Update existing signal (preserve human-set priority and review_note)
        existing_signal.case_count = a
        existing_signal.proportional_reporting_ratio = prr
        existing_signal.signal_strength = signal_strength
        existing_signal.signal_type = signal_type
        existing_signal.trend = trend
        existing_signal.seriousness_ratio = seriousness_ratio
        existing_signal.updated_at = datetime.utcnow()

        # Only auto-set risk_priority if human hasn't overridden it
        if not existing_signal.review_note:
            existing_signal.risk_priority = auto_priority

        # Auto-escalate STRONG new signals
        if signal_strength == "STRONG" and existing_signal.signal_status == "NEW":
            existing_signal.signal_status = "ESCALATED"

        result["signals_updated"] = 1
    else:
        # Create new signal if it meets minimum threshold
        if a >= thresholds["min_case_count"] and prr >= thresholds["prr_threshold"]:
            new_signal = SafetySignal(
                drug_name=drug,
                adverse_event=event,
                signal_type=signal_type,
                case_count=a,
                proportional_reporting_ratio=prr,
                signal_strength=signal_strength,
                trend=trend,
                seriousness_ratio=seriousness_ratio,
                risk_priority=auto_priority,
                is_active=True,
                signal_status="NEW",
                detected_at=datetime.utcnow()
            )
            db.add(new_signal)
            db.flush()

            # Log signal detection in PV audit trail
            try:
                from app.services.pv_audit_service import PVAuditService
                PVAuditService.log_signal_detected(
                    db,
                    signal_id=new_signal.signal_id,
                    drug=drug,
                    event=event,
                    prr=prr,
                    case_count=a,
                )
            except Exception:
                pass  # Don't fail signal creation if audit logging fails

            # Log in governance audit trail
            try:
                from app.services.audit_service import AuditService
                AuditService.log_signal_generated(
                    db,
                    signal_id=new_signal.signal_id,
                    drug_name=drug,
                    adverse_event=event,
                    prr=prr,
                    case_count=a,
                    signal_strength=signal_strength,
                )
            except Exception:
                pass

            result["new_signals"] = 1

    db.commit()
    return result


async def bulk_evaluate_signals(db: Session) -> Dict[str, Any]:
    """
    Bulk evaluate all drug-event combinations to detect signals.
    Should be run periodically (e.g., daily) or on demand.
    """

    # Get all unique drug-event combinations with count >= minimum
    combinations = db.query(
        AECase.suspect_drug,
        AECase.adverse_event,
        func.count(AECase.case_id).label('count')
    ).group_by(
        AECase.suspect_drug,
        AECase.adverse_event
    ).having(
        func.count(AECase.case_id) >= SIGNAL_THRESHOLDS["min_case_count"]
    ).all()

    signals_created = 0
    signals_updated = 0

    for combo in combinations:
        drug, event, count = combo

        # Create a lightweight case object for evaluation
        dummy_case = AECase(
            suspect_drug=drug,
            adverse_event=event
        )

        result = await evaluate_signals_for_case(dummy_case, db)
        signals_created += result.get("new_signals", 0)
        signals_updated += result.get("signals_updated", 0)

    return {
        "combinations_evaluated": len(combinations),
        "signals_created": signals_created,
        "signals_updated": signals_updated,
        "thresholds": SIGNAL_THRESHOLDS,
    }


def get_signal_thresholds() -> Dict[str, Any]:
    """Return current configurable thresholds."""
    return SIGNAL_THRESHOLDS
