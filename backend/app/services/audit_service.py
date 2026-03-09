"""
Audit Service for Feature 7: Governance, Audit, and Human Oversight Layer
Logs all AI decisions, human reviews, and overrides for regulatory compliance.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.models.audit import AuditLog
from app.models.case import AECase
from app.models.user import User


class AuditService:
    """Service for creating audit trail entries"""
    
    @staticmethod
    def log_ai_decision(
        db: Session,
        case_id: UUID,
        decision_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log AI decision generation
        
        Args:
            case_id: Case UUID
            decision_data: AI decision details (risk, priority, recommended_actions, confidence)
            user_id: User who triggered the analysis (optional)
        """
        audit_entry = AuditLog(
            activity_type="AI_DECISION_GENERATED",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            after_state={
                "risk_level": decision_data.get("risk_level"),
                "priority": decision_data.get("priority"),
                "confidence": decision_data.get("confidence"),
                "recommended_actions": decision_data.get("recommended_actions"),
                "actor_type": "AI"
            },
            change_description=f"AI analyzed case and determined risk level: {decision_data.get('risk_level')}",
            regulatory_impact=True,
            gdpr_relevant=True
        )
        
        db.add(audit_entry)
        db.commit()
        return audit_entry
    
    @staticmethod
    def log_human_review(
        db: Session,
        case_id: UUID,
        user_id: str,
        review_note: str,
        decision: str
    ) -> AuditLog:
        """
        Log human review of AI decision
        
        Args:
            case_id: Case UUID
            user_id: Reviewer user ID
            review_note: Human review notes
            decision: APPROVE or OVERRIDE
        """
        audit_entry = AuditLog(
            activity_type="HUMAN_REVIEW_ADDED",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            after_state={
                "decision": decision,
                "review_note": review_note,
                "actor_type": "HUMAN",
                "timestamp": datetime.utcnow().isoformat()
            },
            change_description=f"Human reviewer {decision.lower()}d AI decision: {review_note[:100]}",
            regulatory_impact=True,
            gdpr_relevant=True
        )
        
        db.add(audit_entry)
        db.commit()
        return audit_entry
    
    @staticmethod
    def log_decision_override(
        db: Session,
        case_id: UUID,
        user_id: str,
        override_reason: str,
        previous_decision: Dict[str, Any],
        new_decision: Dict[str, Any]
    ) -> AuditLog:
        """
        Log human override of AI decision
        
        Args:
            case_id: Case UUID
            user_id: User who overrode decision
            override_reason: Mandatory reason for override
            previous_decision: Original AI decision
            new_decision: New human decision
        """
        audit_entry = AuditLog(
            activity_type="AI_DECISION_OVERRIDDEN",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            before_state={
                "risk_level": previous_decision.get("risk_level"),
                "priority": previous_decision.get("priority"),
                "actor_type": "AI"
            },
            after_state={
                "risk_level": new_decision.get("risk_level"),
                "priority": new_decision.get("priority"),
                "override_reason": override_reason,
                "actor_type": "HUMAN",
                "human_final": True
            },
            change_description=f"AI decision overridden by human: {override_reason[:100]}",
            regulatory_impact=True,
            gdpr_relevant=True
        )
        
        db.add(audit_entry)
        db.commit()
        return audit_entry
    
    @staticmethod
    def log_followup_sent(
        db: Session,
        case_id: UUID,
        user_id: Optional[str],
        followup_data: Dict[str, Any]
    ) -> AuditLog:
        """
        Log follow-up sent to reporter
        
        Args:
            case_id: Case UUID
            user_id: User who approved sending (or AI if automatic)
            followup_data: Follow-up details (channel, questions_count)
        """
        actor_type = "HUMAN" if user_id else "AI"
        
        audit_entry = AuditLog(
            activity_type="FOLLOWUP_SENT",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            after_state={
                "channel": followup_data.get("channel"),
                "questions_count": followup_data.get("questions_count"),
                "actor_type": actor_type
            },
            change_description=f"Follow-up questions sent via {followup_data.get('channel')} ({actor_type})",
            regulatory_impact=True,
            gdpr_relevant=True
        )
        
        db.add(audit_entry)
        db.commit()
        return audit_entry
    
    @staticmethod
    def log_case_status_change(
        db: Session,
        case_id: UUID,
        user_id: Optional[str],
        old_status: str,
        new_status: str,
        reason: Optional[str] = None
    ) -> AuditLog:
        """
        Log case status change
        
        Args:
            case_id: Case UUID
            user_id: User who changed status (or AI if automatic)
            old_status: Previous status
            new_status: New status
            reason: Optional reason for change
        """
        actor_type = "HUMAN" if user_id else "AI"
        
        audit_entry = AuditLog(
            activity_type="CASE_STATUS_CHANGED",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            before_state={"status": old_status},
            after_state={
                "status": new_status,
                "actor_type": actor_type,
                "reason": reason
            },
            change_description=f"Case status changed from {old_status} to {new_status} ({actor_type})",
            regulatory_impact=True,
            gdpr_relevant=False
        )
        
        db.add(audit_entry)
        db.commit()
        return audit_entry
    
    @staticmethod
    def get_case_audit_log(
        db: Session,
        case_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit log for a specific case
        
        Args:
            case_id: Case UUID
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries with formatted data
        """
        logs = db.query(AuditLog).filter(
            AuditLog.entity_id == case_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "log_id": str(log.log_id),
                "activity_type": log.activity_type,
                "user_id": log.user_id,
                "actor_type": log.after_state.get("actor_type") if log.after_state else None,
                "before_state": log.before_state,
                "after_state": log.after_state,
                "change_description": log.change_description,
                "regulatory_impact": log.regulatory_impact,
                "gdpr_relevant": log.gdpr_relevant,
                "timestamp": log.timestamp.isoformat(),
                "human_final": log.after_state.get("human_final", False) if log.after_state else False
            }
            for log in logs
        ]
    
    @staticmethod
    def get_all_audit_logs(
        db: Session,
        activity_type: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all audit logs with optional filtering
        
        Args:
            activity_type: Filter by activity type (optional)
            limit: Maximum number of entries
            
        Returns:
            List of audit log entries
        """
        query = db.query(AuditLog)
        
        if activity_type:
            query = query.filter(AuditLog.activity_type == activity_type)
        
        logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "log_id": str(log.log_id),
                "activity_type": log.activity_type,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "user_id": log.user_id,
                "change_description": log.change_description,
                "regulatory_impact": log.regulatory_impact,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    
    @staticmethod
    def log_followup_sent(
        db: Session,
        case_id: UUID,
        channel: str,
        question_count: int,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log automated follow-up sent
        
        Args:
            case_id: Case UUID
            channel: Communication channel (PHONE/EMAIL/WHATSAPP)
            question_count: Number of questions sent
            user_id: User who triggered (optional - can be system)
        """
        audit_entry = AuditLog(
            activity_type="FOLLOWUP_SENT",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            after_state={
                "channel": channel,
                "question_count": question_count,
                "actor_type": "SYSTEM"
            },
            change_description=f"Automated follow-up sent via {channel} with {question_count} questions",
            regulatory_impact=True,
            gdpr_relevant=True
        )
        
        db.add(audit_entry)
        db.commit()
        
        return audit_entry

    # ── Case created audit ──────────────────────────────────
    @staticmethod
    def log_case_created(
        db: Session,
        case_id: UUID,
        intake_source: str,
        primaryid: Optional[int] = None,
        suspect_drug: Optional[str] = None,
        adverse_event: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AuditLog:
        """Log new case creation (CSV upload, PDF upload, or manual entry)."""
        audit_entry = AuditLog(
            activity_type="CASE_CREATED",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            after_state={
                "intake_source": intake_source,
                "primaryid": primaryid,
                "suspect_drug": suspect_drug,
                "adverse_event": adverse_event,
                "actor_type": "SYSTEM",
            },
            change_description=(
                f"New case created via {intake_source} — "
                f"drug: {suspect_drug or 'N/A'}, event: {adverse_event or 'N/A'}"
            ),
            regulatory_impact=True,
            gdpr_relevant=True,
        )
        db.add(audit_entry)
        db.commit()
        return audit_entry

    # ── Signal generated audit ───────────────────────────────
    @staticmethod
    def log_signal_generated(
        db: Session,
        signal_id: UUID,
        drug_name: str,
        adverse_event: str,
        prr: float,
        case_count: int,
        signal_strength: str,
    ) -> AuditLog:
        """Log new safety signal detection."""
        audit_entry = AuditLog(
            activity_type="SIGNAL_GENERATED",
            entity_type="SIGNAL",
            entity_id=signal_id,
            user_id=None,
            after_state={
                "drug_name": drug_name,
                "adverse_event": adverse_event,
                "prr": round(prr, 2),
                "case_count": case_count,
                "signal_strength": signal_strength,
                "actor_type": "AI",
            },
            change_description=(
                f"Safety signal detected: {drug_name} ↔ {adverse_event} "
                f"(PRR={prr:.2f}, cases={case_count}, strength={signal_strength})"
            ),
            regulatory_impact=True,
            gdpr_relevant=False,
        )
        db.add(audit_entry)
        db.commit()
        return audit_entry

    # ── Regulatory process started audit ─────────────────────
    @staticmethod
    def log_regulatory_process_started(
        db: Session,
        signal_id: UUID,
        workflow_id: UUID,
        user_id: str,
        due_date: Optional[str] = None,
    ) -> AuditLog:
        """Log start of a regulatory workflow / expedited reporting process."""
        audit_entry = AuditLog(
            activity_type="REGULATORY_PROCESS_STARTED",
            entity_type="SIGNAL",
            entity_id=signal_id,
            user_id=user_id,
            after_state={
                "workflow_id": str(workflow_id),
                "due_date": due_date,
                "actor_type": "HUMAN",
            },
            change_description=(
                f"Regulatory workflow started for signal {str(signal_id)[:8]}… "
                f"(due: {due_date or 'TBD'})"
            ),
            regulatory_impact=True,
            gdpr_relevant=False,
        )
        db.add(audit_entry)
        db.commit()
        return audit_entry

    # ── Response received audit ──────────────────────────────
    @staticmethod
    def log_followup_response_received(
        db: Session,
        case_id: UUID,
        channel: str,
        fields_updated: list,
        response_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AuditLog:
        """Log that a reporter response was received and processed."""
        audit_entry = AuditLog(
            activity_type="FOLLOWUP_RESPONSE_RECEIVED",
            entity_type="CASE",
            entity_id=case_id,
            user_id=user_id,
            after_state={
                "channel": channel,
                "fields_updated": fields_updated,
                "response_id": response_id,
                "attempt_id": attempt_id,
                "actor_type": "REPORTER",
            },
            change_description=(
                f"Reporter response received via {channel}: "
                f"{len(fields_updated)} field(s) updated — {', '.join(fields_updated) if fields_updated else 'none'}"
            ),
            regulatory_impact=True,
            gdpr_relevant=True,
        )
        db.add(audit_entry)
        db.commit()
        return audit_entry
