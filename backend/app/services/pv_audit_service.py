"""
Pharmacovigilance Audit Trail Service
======================================

Immutable, append-only logging for every critical PV action.
All methods create new records — NO updates or deletes.

Designed for FDA 21 CFR Part 11, EMA GVP, MHRA compliance.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
import uuid

from app.models.pv_audit_trail import PVAuditTrail


class PVAuditService:
    """Immutable audit trail service for pharmacovigilance compliance."""

    # ─────────────────────────────────────────────
    # CORE WRITE METHOD (all others delegate here)
    # ─────────────────────────────────────────────

    @staticmethod
    def _create_entry(
        db: Session,
        *,
        action_type: str,
        description: str,
        actor_type: str = "SYSTEM",
        actor_id: Optional[str] = None,
        case_id: Optional[UUID] = None,
        signal_id: Optional[UUID] = None,
        previous_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        decision_metadata: Optional[Dict] = None,
        model_version: Optional[str] = None,
        confidence_score: Optional[float] = None,
        channel: Optional[str] = None,
        regulatory_impact: bool = True,
    ) -> PVAuditTrail:
        entry = PVAuditTrail(
            audit_id=uuid.uuid4(),
            case_id=case_id,
            timestamp=datetime.utcnow(),
            actor_type=actor_type,
            actor_id=actor_id,
            action_type=action_type,
            previous_value=previous_value,
            new_value=new_value,
            decision_metadata=decision_metadata,
            model_version=model_version,
            confidence_score=confidence_score,
            channel=channel,
            signal_id=signal_id,
            description=description,
            regulatory_impact=regulatory_impact,
        )
        db.add(entry)
        db.flush()  # flush to get audit_id, caller commits
        return entry

    # ─────────────────────────────────────────────
    # CASE LIFECYCLE ACTIONS
    # ─────────────────────────────────────────────

    @staticmethod
    def log_case_created(
        db: Session, case_id: UUID, actor_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="CASE_CREATED",
            description="New adverse event case created",
            actor_type="SYSTEM" if not actor_id else "HUMAN",
            actor_id=actor_id,
            case_id=case_id,
            new_value=metadata,
        )

    @staticmethod
    def log_cioms_parsed(
        db: Session, case_id: UUID, fields_extracted: Dict,
        actor_id: Optional[str] = None,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="CIOMS_PARSED",
            description=f"CIOMS Form-I parsed — {len(fields_extracted)} fields extracted",
            actor_type="SYSTEM",
            actor_id=actor_id,
            case_id=case_id,
            new_value=fields_extracted,
        )

    @staticmethod
    def log_fields_extracted(
        db: Session, case_id: UUID, field_names: List[str],
        source: str = "PDF",
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="FIELDS_EXTRACTED",
            description=f"{len(field_names)} fields extracted from {source}",
            actor_type="SYSTEM",
            case_id=case_id,
            new_value={"fields": field_names, "source": source},
        )

    @staticmethod
    def log_ai_risk_decision(
        db: Session, case_id: UUID, decision_data: Dict,
        model_version: Optional[str] = None,
        confidence: Optional[float] = None,
        actor_id: Optional[str] = None,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="AI_RISK_DECISION",
            description=f"AI risk assessment: {decision_data.get('risk_level', 'N/A')} (confidence {confidence or 0:.2f})",
            actor_type="AI",
            actor_id=actor_id,
            case_id=case_id,
            new_value=decision_data,
            decision_metadata=decision_data,
            model_version=model_version,
            confidence_score=confidence,
        )

    @staticmethod
    def log_ai_followup_decision(
        db: Session, case_id: UUID, decision_data: Dict,
        model_version: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="AI_FOLLOWUP_DECISION",
            description=f"AI follow-up decision: {decision_data.get('action', 'N/A')}",
            actor_type="AI",
            case_id=case_id,
            new_value=decision_data,
            decision_metadata=decision_data,
            model_version=model_version,
            confidence_score=confidence,
        )

    @staticmethod
    def log_human_override(
        db: Session, case_id: UUID, actor_id: str,
        previous_value: Dict, new_value: Dict,
        reason: str,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="HUMAN_OVERRIDE",
            description=f"Human override applied: {reason[:120]}",
            actor_type="HUMAN",
            actor_id=actor_id,
            case_id=case_id,
            previous_value=previous_value,
            new_value=new_value,
            decision_metadata={"reason": reason},
        )

    @staticmethod
    def log_followup_sent(
        db: Session, case_id: UUID, channel: str,
        questions_count: int, sent_to: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="FOLLOWUP_SENT",
            description=f"Follow-up sent via {channel} ({questions_count} questions)",
            actor_type="SYSTEM" if not actor_id else "HUMAN",
            actor_id=actor_id,
            case_id=case_id,
            channel=channel,
            new_value={"questions_count": questions_count, "sent_to": sent_to, "channel": channel},
        )

    @staticmethod
    def log_response_received(
        db: Session, case_id: UUID, channel: str,
        fields_updated: List[str],
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="RESPONSE_RECEIVED",
            description=f"Reporter response via {channel}: {len(fields_updated)} field(s) updated",
            actor_type="REPORTER",
            case_id=case_id,
            channel=channel,
            new_value={"fields_updated": fields_updated, "channel": channel},
        )

    @staticmethod
    def log_reviewer_note(
        db: Session, case_id: UUID, actor_id: str,
        note: str,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="REVIEWER_NOTE_ADDED",
            description=f"Reviewer note added: {note[:80]}",
            actor_type="HUMAN",
            actor_id=actor_id,
            case_id=case_id,
            new_value={"note": note},
        )

    @staticmethod
    def log_lifecycle_stage_change(
        db: Session, case_id: UUID,
        old_stage: str, new_stage: str,
        reason: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="LIFECYCLE_STAGE_CHANGE",
            description=f"Lifecycle: {old_stage} -> {new_stage}" + (f" ({reason})" if reason else ""),
            actor_type="SYSTEM" if not actor_id else "HUMAN",
            actor_id=actor_id,
            case_id=case_id,
            previous_value={"stage": old_stage},
            new_value={"stage": new_stage, "reason": reason},
        )

    @staticmethod
    def log_case_closed(
        db: Session, case_id: UUID, reason: str,
        actor_id: Optional[str] = None,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="CASE_CLOSED",
            description=f"Case closed: {reason[:120]}",
            actor_type="SYSTEM" if not actor_id else "HUMAN",
            actor_id=actor_id,
            case_id=case_id,
            new_value={"reason": reason},
        )

    # ─────────────────────────────────────────────
    # SIGNAL ACTIONS
    # ─────────────────────────────────────────────

    @staticmethod
    def log_signal_detected(
        db: Session, signal_id: UUID,
        drug: str, event: str, prr: float, case_count: int,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="SIGNAL_DETECTED",
            description=f"Signal detected: {drug} -> {event} (PRR={prr:.2f}, cases={case_count})",
            actor_type="SYSTEM",
            signal_id=signal_id,
            new_value={"drug": drug, "event": event, "prr": prr, "case_count": case_count},
        )

    @staticmethod
    def log_signal_reviewed(
        db: Session, signal_id: UUID, actor_id: str,
        note: str, action: str,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="SIGNAL_REVIEWED",
            description=f"Signal reviewed ({action}): {note[:100]}",
            actor_type="HUMAN",
            actor_id=actor_id,
            signal_id=signal_id,
            new_value={"action": action, "note": note},
        )

    @staticmethod
    def log_signal_priority_changed(
        db: Session, signal_id: UUID, actor_id: str,
        old_priority: Optional[str], new_priority: str,
        reason: str,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="SIGNAL_PRIORITY_CHANGED",
            description=f"Signal priority: {old_priority} -> {new_priority}",
            actor_type="HUMAN",
            actor_id=actor_id,
            signal_id=signal_id,
            previous_value={"risk_priority": old_priority},
            new_value={"risk_priority": new_priority, "reason": reason},
        )

    @staticmethod
    def log_signal_false_positive(
        db: Session, signal_id: UUID, actor_id: str,
        reason: str,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="SIGNAL_FALSE_POSITIVE",
            description=f"Signal marked as false positive: {reason[:100]}",
            actor_type="HUMAN",
            actor_id=actor_id,
            signal_id=signal_id,
            new_value={"reason": reason, "status": "FALSE_POSITIVE"},
        )

    @staticmethod
    def log_regulatory_escalation(
        db: Session, signal_id: UUID, actor_id: str,
        workflow_id: UUID, snapshot: Dict,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="REGULATORY_ESCALATION",
            description="Regulatory escalation initiated — signal snapshot frozen",
            actor_type="HUMAN",
            actor_id=actor_id,
            signal_id=signal_id,
            new_value={"workflow_id": str(workflow_id)},
            decision_metadata=snapshot,
        )

    @staticmethod
    def log_regulatory_workflow_created(
        db: Session, signal_id: UUID, workflow_id: UUID,
        actor_id: str, due_date: str,
    ) -> PVAuditTrail:
        return PVAuditService._create_entry(
            db,
            action_type="REGULATORY_WORKFLOW_CREATED",
            description=f"Regulatory workflow created (due {due_date})",
            actor_type="HUMAN",
            actor_id=actor_id,
            signal_id=signal_id,
            new_value={"workflow_id": str(workflow_id), "due_date": due_date},
        )

    # ─────────────────────────────────────────────
    # READ METHODS
    # ─────────────────────────────────────────────

    @staticmethod
    def get_case_audit_trail(
        db: Session, case_id: UUID,
        action_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Retrieve chronological audit trail for a case."""
        q = db.query(PVAuditTrail).filter(PVAuditTrail.case_id == case_id)
        if action_type:
            q = q.filter(PVAuditTrail.action_type == action_type)
        entries = q.order_by(desc(PVAuditTrail.timestamp)).offset(offset).limit(limit).all()
        return [PVAuditService._format_entry(e) for e in entries]

    @staticmethod
    def get_signal_audit_trail(
        db: Session, signal_id: UUID,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit trail for a signal."""
        entries = (
            db.query(PVAuditTrail)
            .filter(PVAuditTrail.signal_id == signal_id)
            .order_by(desc(PVAuditTrail.timestamp))
            .limit(limit)
            .all()
        )
        return [PVAuditService._format_entry(e) for e in entries]

    @staticmethod
    def get_global_audit_trail(
        db: Session,
        action_type: Optional[str] = None,
        actor_type: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Retrieve system-wide audit trail with filters."""
        q = db.query(PVAuditTrail)
        if action_type:
            q = q.filter(PVAuditTrail.action_type == action_type)
        if actor_type:
            q = q.filter(PVAuditTrail.actor_type == actor_type)
        entries = q.order_by(desc(PVAuditTrail.timestamp)).offset(offset).limit(limit).all()
        return [PVAuditService._format_entry(e) for e in entries]

    @staticmethod
    def get_audit_stats(db: Session) -> Dict[str, Any]:
        """Get aggregate audit statistics."""
        from sqlalchemy import func
        total = db.query(func.count(PVAuditTrail.audit_id)).scalar() or 0
        by_actor = dict(
            db.query(PVAuditTrail.actor_type, func.count(PVAuditTrail.audit_id))
            .group_by(PVAuditTrail.actor_type)
            .all()
        )
        by_action = dict(
            db.query(PVAuditTrail.action_type, func.count(PVAuditTrail.audit_id))
            .group_by(PVAuditTrail.action_type)
            .all()
        )
        return {
            "total_entries": total,
            "by_actor_type": by_actor,
            "by_action_type": by_action,
        }

    # ─────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────

    @staticmethod
    def _format_entry(entry: PVAuditTrail) -> Dict[str, Any]:
        return {
            "audit_id": str(entry.audit_id),
            "case_id": str(entry.case_id) if entry.case_id else None,
            "signal_id": str(entry.signal_id) if entry.signal_id else None,
            "timestamp": entry.timestamp.isoformat(),
            "actor_type": entry.actor_type,
            "actor_id": entry.actor_id,
            "action_type": entry.action_type,
            "previous_value": entry.previous_value,
            "new_value": entry.new_value,
            "decision_metadata": entry.decision_metadata,
            "model_version": entry.model_version,
            "confidence_score": entry.confidence_score,
            "channel": entry.channel,
            "description": entry.description,
            "regulatory_impact": entry.regulatory_impact,
        }
