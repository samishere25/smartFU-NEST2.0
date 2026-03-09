"""
Production Lifecycle Database Service
======================================

Feature-4: Database-backed lifecycle tracking service.

This replaces the in-memory demo storage with proper
PostgreSQL database operations using SQLAlchemy.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import uuid
import json

from app.models.lifecycle_tracker import (
    FollowUpLifecycle,
    LifecycleAttempt,
    LifecycleAuditLog
)
from app.services.lifecycle_tracker import (
    get_policy,
    HCP_POLICY,
    NON_HCP_POLICY
)

logger = logging.getLogger(__name__)


class LifecycleDBService:
    """
    Production database service for lifecycle tracking.
    
    All operations are persisted to PostgreSQL.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # CREATE / INITIALIZE
    # ========================================================================
    
    def initialize_lifecycle(
        self,
        case_id: str,
        reporter_type: str,
        seriousness_level: str,
        case_created_at: datetime = None,
        initial_completeness: float = 0.0
    ) -> FollowUpLifecycle:
        """
        Initialize lifecycle tracking for a new case in database.
        """
        case_created_at = case_created_at or datetime.utcnow()
        
        # Check if lifecycle already exists
        existing = self.get_lifecycle_by_case_id(case_id)
        if existing:
            logger.info(f"Lifecycle already exists for case {case_id}, returning existing")
            return existing
        
        # Determine HCP vs Non-HCP
        hcp_types = ["MD", "HP", "PH", "HCP", "RPH", "RN"]
        is_hcp = reporter_type.upper() in hcp_types
        reporter_category = "HCP" if is_hcp else "NON_HCP"
        
        # Get policy
        policy = get_policy(reporter_type)
        
        # Calculate regulatory deadline
        if seriousness_level in ["high", "critical"]:
            deadline_days = 7
            deadline_type = "7_day"
        else:
            deadline_days = 15
            deadline_type = "15_day"
        
        regulatory_deadline = case_created_at + timedelta(days=deadline_days)
        days_remaining = (regulatory_deadline - datetime.utcnow()).days
        
        # Create lifecycle record
        lifecycle = FollowUpLifecycle(
            lifecycle_id=uuid.uuid4(),
            case_id=uuid.UUID(case_id) if isinstance(case_id, str) else case_id,
            reporter_type=reporter_category,
            reporter_subtype=reporter_type.upper(),
            attempt_count=0,
            max_attempts=policy.max_attempts,
            reminder_interval_hours=policy.reminder_interval_hours,
            response_status="pending",
            questions_per_round=policy.questions_per_round,
            escalation_status="none",
            seriousness_level=seriousness_level,
            regulatory_deadline=regulatory_deadline,
            days_remaining=days_remaining,
            deadline_type=deadline_type,
            completeness_score=initial_completeness,
            safety_confidence_score=0.0,
            target_completeness=0.85,
            mandatory_fields_complete=False,
            dead_case_flag=False,
            lifecycle_status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(lifecycle)
        
        # Create audit log entry
        self._create_audit_log(
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            action_type="CASE_CREATED",
            action_description=f"Lifecycle initialized for {reporter_category} reporter",
            reason=f"Seriousness: {seriousness_level}, Deadline: {deadline_type}",
            policy_applied=f"{reporter_category}_POLICY"
        )
        
        self.db.commit()
        self.db.refresh(lifecycle)
        
        logger.info(f"✅ Lifecycle initialized in DB for case {case_id}: {reporter_category}, {deadline_type}")
        
        return lifecycle
    
    # ========================================================================
    # READ
    # ========================================================================
    
    def get_lifecycle_by_case_id(self, case_id: str) -> Optional[FollowUpLifecycle]:
        """Get lifecycle by case ID (string or UUID)."""
        try:
            case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
            return self.db.query(FollowUpLifecycle).filter(
                FollowUpLifecycle.case_id == case_uuid
            ).first()
        except ValueError:
            # If case_id is not a valid UUID, try string match
            return self.db.query(FollowUpLifecycle).filter(
                FollowUpLifecycle.case_id == case_id
            ).first()
    
    def get_lifecycle_by_id(self, lifecycle_id: str) -> Optional[FollowUpLifecycle]:
        """Get lifecycle by lifecycle ID."""
        lifecycle_uuid = uuid.UUID(lifecycle_id) if isinstance(lifecycle_id, str) else lifecycle_id
        return self.db.query(FollowUpLifecycle).filter(
            FollowUpLifecycle.lifecycle_id == lifecycle_uuid
        ).first()
    
    def get_attempts(self, lifecycle_id: uuid.UUID) -> List[LifecycleAttempt]:
        """Get all attempts for a lifecycle."""
        return self.db.query(LifecycleAttempt).filter(
            LifecycleAttempt.lifecycle_id == lifecycle_id
        ).order_by(LifecycleAttempt.sent_at.asc()).all()
    
    def get_audit_log(self, lifecycle_id: uuid.UUID, limit: int = 50) -> List[LifecycleAuditLog]:
        """Get audit log for a lifecycle."""
        return self.db.query(LifecycleAuditLog).filter(
            LifecycleAuditLog.lifecycle_id == lifecycle_id
        ).order_by(LifecycleAuditLog.timestamp.desc()).limit(limit).all()
    
    # ========================================================================
    # UPDATE OPERATIONS
    # ========================================================================
    
    def record_followup_sent(
        self,
        lifecycle: FollowUpLifecycle,
        questions_sent: List[Dict],
        channel: str,
        sent_to: str = None
    ) -> FollowUpLifecycle:
        """Record that a follow-up was sent."""
        now = datetime.utcnow()
        
        # Update lifecycle
        lifecycle.attempt_count += 1
        lifecycle.last_attempt_at = now
        lifecycle.total_questions_sent = (lifecycle.total_questions_sent or 0) + len(questions_sent)
        lifecycle.next_reminder_due = now + timedelta(hours=lifecycle.reminder_interval_hours or 24)
        lifecycle.lifecycle_status = "awaiting_response"
        lifecycle.response_status = "pending"
        lifecycle.updated_at = now
        
        # Update days remaining
        if lifecycle.regulatory_deadline:
            lifecycle.days_remaining = (lifecycle.regulatory_deadline - now).days
        
        # Create attempt record
        attempt = LifecycleAttempt(
            attempt_id=uuid.uuid4(),
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            attempt_number=lifecycle.attempt_count,
            attempt_type="initial" if lifecycle.attempt_count == 1 else "followup",
            channel=channel,
            sent_to=sent_to,
            questions_sent=questions_sent,
            questions_count=len(questions_sent),
            sent_at=now,
            response_received=False,
            compliance_24h_met=True,
            created_at=now
        )
        self.db.add(attempt)
        
        # Audit log
        self._create_audit_log(
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            action_type="FOLLOWUP_SENT",
            action_description=f"Follow-up #{lifecycle.attempt_count} sent via {channel}",
            reason=f"Questions: {len(questions_sent)}"
        )
        
        self.db.commit()
        self.db.refresh(lifecycle)
        
        logger.info(f"📤 Follow-up #{lifecycle.attempt_count} recorded in DB for case {lifecycle.case_id}")
        
        return lifecycle
    
    def record_response_received(
        self,
        lifecycle: FollowUpLifecycle,
        questions_answered: int,
        completeness_score: float,
        safety_confidence: float,
        is_complete: bool = False
    ) -> FollowUpLifecycle:
        """Record that a response was received from reporter."""
        now = datetime.utcnow()
        
        # Update lifecycle
        lifecycle.last_response_at = now
        lifecycle.total_questions_answered = (lifecycle.total_questions_answered or 0) + questions_answered
        lifecycle.completeness_score = completeness_score
        lifecycle.safety_confidence_score = safety_confidence
        lifecycle.updated_at = now
        
        # Determine response status
        if is_complete or completeness_score >= (lifecycle.target_completeness or 0.85):
            lifecycle.response_status = "complete"
            lifecycle.lifecycle_status = "completed"
            lifecycle.mandatory_fields_complete = True
        elif questions_answered > 0:
            lifecycle.response_status = "partial"
            lifecycle.lifecycle_status = "active"
        
        # Update last attempt
        last_attempt = self.db.query(LifecycleAttempt).filter(
            LifecycleAttempt.lifecycle_id == lifecycle.lifecycle_id
        ).order_by(LifecycleAttempt.sent_at.desc()).first()
        
        if last_attempt:
            last_attempt.response_received = True
            last_attempt.response_received_at = now
            # Increment questions_answered (not set) to track cumulative per attempt
            last_attempt.questions_answered = (last_attempt.questions_answered or 0) + questions_answered
            last_attempt.response_type = "full" if is_complete else "partial"

        # Audit log
        self._create_audit_log(
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            action_type="RESPONSE_RECEIVED",
            action_description=f"Answer received: {lifecycle.total_questions_answered} total answered, completeness {completeness_score:.0%}",
            reason=f"Completeness: {completeness_score:.0%}, Status: {lifecycle.response_status}"
        )
        
        self.db.commit()
        self.db.refresh(lifecycle)
        
        logger.info(f"📥 Response recorded in DB for case {lifecycle.case_id}: {lifecycle.response_status}")
        
        return lifecycle
    
    def record_reminder_sent(
        self,
        lifecycle: FollowUpLifecycle,
        channel: str
    ) -> FollowUpLifecycle:
        """Record that a reminder was sent."""
        now = datetime.utcnow()
        
        lifecycle.attempt_count += 1
        lifecycle.last_attempt_at = now
        lifecycle.next_reminder_due = now + timedelta(hours=lifecycle.reminder_interval_hours or 24)
        lifecycle.updated_at = now
        
        if lifecycle.regulatory_deadline:
            lifecycle.days_remaining = (lifecycle.regulatory_deadline - now).days
        
        # Update last attempt
        last_attempt = self.db.query(LifecycleAttempt).filter(
            LifecycleAttempt.lifecycle_id == lifecycle.lifecycle_id
        ).order_by(LifecycleAttempt.sent_at.desc()).first()
        
        if last_attempt:
            last_attempt.reminder_sent = True
            last_attempt.reminder_sent_at = now
        
        self._create_audit_log(
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            action_type="REMINDER_SENT",
            action_description=f"24-hour compliance reminder #{lifecycle.attempt_count} sent",
            reason="24-hour compliance rule"
        )
        
        self.db.commit()
        self.db.refresh(lifecycle)
        
        return lifecycle
    
    def trigger_escalation(
        self,
        lifecycle: FollowUpLifecycle,
        reason: str,
        escalate_to: str
    ) -> FollowUpLifecycle:
        """Trigger escalation for a case."""
        now = datetime.utcnow()
        
        if escalate_to == "medical_team":
            escalation_status = "escalated_to_medical"
        else:
            escalation_status = "escalated_to_reviewer"
        
        lifecycle.escalation_status = escalation_status
        lifecycle.escalation_reason = reason
        lifecycle.escalated_at = now
        lifecycle.escalated_to = escalate_to
        lifecycle.lifecycle_status = "escalated"
        lifecycle.updated_at = now
        
        self._create_audit_log(
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            action_type="ESCALATION_TRIGGERED",
            action_description=f"Case escalated to {escalate_to}",
            reason=reason
        )
        
        self.db.commit()
        self.db.refresh(lifecycle)
        
        logger.warning(f"🚨 Case {lifecycle.case_id} ESCALATED to {escalate_to}")
        
        return lifecycle
    
    def mark_dead_case(
        self,
        lifecycle: FollowUpLifecycle,
        reason: str,
        closed_by: str = "system"
    ) -> FollowUpLifecycle:
        """Mark case as dead."""
        now = datetime.utcnow()
        
        lifecycle.dead_case_flag = True
        lifecycle.closure_reason = reason
        lifecycle.closed_at = now
        lifecycle.closed_by = closed_by
        lifecycle.lifecycle_status = "dead_case"
        lifecycle.response_status = "no_response"
        lifecycle.updated_at = now
        
        self._create_audit_log(
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            action_type="DEAD_CASE_MARKED",
            action_description="Case marked as dead",
            reason=reason,
            actor=closed_by
        )
        
        self.db.commit()
        self.db.refresh(lifecycle)
        
        logger.warning(f"☠️ Case {lifecycle.case_id} marked as DEAD")
        
        return lifecycle
    
    def close_case_success(
        self,
        lifecycle: FollowUpLifecycle,
        closed_by: str = "system"
    ) -> FollowUpLifecycle:
        """Close case successfully."""
        now = datetime.utcnow()
        
        lifecycle.lifecycle_status = "closed"
        lifecycle.response_status = "complete"
        lifecycle.closure_reason = "Target completeness achieved"
        lifecycle.closed_at = now
        lifecycle.closed_by = closed_by
        lifecycle.updated_at = now
        
        self._create_audit_log(
            lifecycle_id=lifecycle.lifecycle_id,
            case_id=lifecycle.case_id,
            action_type="CASE_CLOSED",
            action_description="Case closed successfully",
            reason=f"Completeness: {lifecycle.completeness_score:.0%}",
            actor=closed_by
        )
        
        self.db.commit()
        self.db.refresh(lifecycle)
        
        logger.info(f"✅ Case {lifecycle.case_id} CLOSED successfully")
        
        return lifecycle
    
    def update_deadline_awareness(self, lifecycle: FollowUpLifecycle) -> FollowUpLifecycle:
        """Update deadline awareness."""
        if not lifecycle.regulatory_deadline:
            return lifecycle
        
        now = datetime.utcnow()
        days_remaining = (lifecycle.regulatory_deadline - now).days
        lifecycle.days_remaining = days_remaining
        
        policy = get_policy(lifecycle.reporter_subtype or "NON_HCP")
        
        if days_remaining <= 0:
            if lifecycle.escalation_status in ["none", "flagged", "urgent"]:
                lifecycle = self.trigger_escalation(
                    lifecycle,
                    reason="Regulatory deadline passed!",
                    escalate_to="medical_team"
                )
        elif days_remaining <= policy.deadline_warning_days:
            if lifecycle.escalation_status == "none":
                lifecycle.escalation_status = "urgent"
                self._create_audit_log(
                    lifecycle_id=lifecycle.lifecycle_id,
                    case_id=lifecycle.case_id,
                    action_type="DEADLINE_WARNING",
                    action_description=f"Only {days_remaining} days until deadline",
                    reason="Deadline approaching"
                )
        
        lifecycle.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(lifecycle)
        
        return lifecycle
    
    # ========================================================================
    # CHECK OPERATIONS
    # ========================================================================
    
    def is_reminder_due(self, lifecycle: FollowUpLifecycle) -> Tuple[bool, str]:
        """Check if a reminder should be sent."""
        if lifecycle.response_status == "complete":
            return False, "Case already complete"
        
        if lifecycle.dead_case_flag:
            return False, "Case marked as dead"
        
        if lifecycle.lifecycle_status in ["completed", "closed", "dead_case"]:
            return False, f"Case status is {lifecycle.lifecycle_status}"
        
        if not lifecycle.next_reminder_due:
            return False, "No reminder scheduled"
        
        now = datetime.utcnow()
        
        if now >= lifecycle.next_reminder_due:
            return True, "24-hour compliance reminder due"
        
        hours_remaining = (lifecycle.next_reminder_due - now).total_seconds() / 3600
        return False, f"Reminder due in {hours_remaining:.1f} hours"
    
    def check_escalation_needed(self, lifecycle: FollowUpLifecycle) -> Tuple[bool, str, str]:
        """Check if escalation is needed."""
        policy = get_policy(lifecycle.reporter_subtype or "NON_HCP")
        
        if lifecycle.escalation_status in ["escalated_to_reviewer", "escalated_to_medical"]:
            return False, "Already escalated", None
        
        if lifecycle.attempt_count >= policy.escalation_after_attempts:
            return True, f"Reached {lifecycle.attempt_count} attempts", policy.escalate_to
        
        if lifecycle.days_remaining is not None and lifecycle.days_remaining <= policy.deadline_warning_days:
            return True, f"Only {lifecycle.days_remaining} days remaining", policy.escalate_to
        
        if lifecycle.seriousness_level in ["high", "critical"] and lifecycle.response_status == "pending" and lifecycle.attempt_count >= 2:
            return True, f"High seriousness with no response after {lifecycle.attempt_count} attempts", "medical_team"
        
        return False, "No escalation needed", None
    
    def check_dead_case(self, lifecycle: FollowUpLifecycle) -> Tuple[bool, str]:
        """Check if case should be marked as dead."""
        policy = get_policy(lifecycle.reporter_subtype or "NON_HCP")
        
        if not policy.allow_auto_dead_case:
            if lifecycle.escalation_status not in ["escalated_to_reviewer", "escalated_to_medical"]:
                return False, "HCP policy requires escalation before dead case"
        
        if lifecycle.response_status == "complete" or (lifecycle.completeness_score or 0) >= (lifecycle.target_completeness or 0.85):
            return False, "Case is complete"
        
        if lifecycle.attempt_count >= lifecycle.max_attempts and lifecycle.response_status in ["pending", "no_response"]:
            return True, f"No response after {lifecycle.attempt_count} attempts (max: {lifecycle.max_attempts})"
        
        return False, "Case still active"
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _create_audit_log(
        self,
        lifecycle_id: uuid.UUID,
        case_id: uuid.UUID,
        action_type: str,
        action_description: str,
        reason: str = None,
        actor: str = "system",
        policy_applied: str = None
    ):
        """Create an audit log entry in DB."""
        audit = LifecycleAuditLog(
            log_id=uuid.uuid4(),
            lifecycle_id=lifecycle_id,
            case_id=case_id,
            action_type=action_type,
            action_description=action_description,
            reason=reason,
            actor=actor,
            actor_type="system" if actor == "system" else "human",
            policy_applied=policy_applied,
            timestamp=datetime.utcnow()
        )
        self.db.add(audit)
    
    def lifecycle_to_dict(self, lifecycle: FollowUpLifecycle) -> Dict[str, Any]:
        """Convert lifecycle model to dictionary."""
        attempts = self.get_attempts(lifecycle.lifecycle_id)
        audit_log = self.get_audit_log(lifecycle.lifecycle_id, limit=20)
        
        return {
            "lifecycle_id": str(lifecycle.lifecycle_id),
            "case_id": str(lifecycle.case_id),
            "reporter_type": lifecycle.reporter_type,
            "reporter_subtype": lifecycle.reporter_subtype,
            "attempt_count": lifecycle.attempt_count or 0,
            "max_attempts": lifecycle.max_attempts or 3,
            "last_attempt_at": lifecycle.last_attempt_at.isoformat() if lifecycle.last_attempt_at else None,
            "next_reminder_due": lifecycle.next_reminder_due.isoformat() if lifecycle.next_reminder_due else None,
            "reminder_interval_hours": lifecycle.reminder_interval_hours or 24,
            "response_status": lifecycle.response_status or "pending",
            "last_response_at": lifecycle.last_response_at.isoformat() if lifecycle.last_response_at else None,
            "total_questions_sent": lifecycle.total_questions_sent or 0,
            "total_questions_answered": lifecycle.total_questions_answered or 0,
            "questions_per_round": lifecycle.questions_per_round or 3,
            "escalation_status": lifecycle.escalation_status or "none",
            "escalation_reason": lifecycle.escalation_reason,
            "escalated_at": lifecycle.escalated_at.isoformat() if lifecycle.escalated_at else None,
            "escalated_to": lifecycle.escalated_to,
            "seriousness_level": lifecycle.seriousness_level or "medium",
            "regulatory_deadline": lifecycle.regulatory_deadline.isoformat() if lifecycle.regulatory_deadline else None,
            "days_remaining": lifecycle.days_remaining,
            "deadline_type": lifecycle.deadline_type or "15_day",
            "completeness_score": lifecycle.completeness_score or 0.0,
            "safety_confidence_score": lifecycle.safety_confidence_score or 0.0,
            "target_completeness": lifecycle.target_completeness or 0.85,
            "mandatory_fields_complete": lifecycle.mandatory_fields_complete or False,
            "dead_case_flag": lifecycle.dead_case_flag or False,
            "closure_reason": lifecycle.closure_reason,
            "closed_at": lifecycle.closed_at.isoformat() if lifecycle.closed_at else None,
            "lifecycle_status": lifecycle.lifecycle_status or "active",
            "policy_applied": f"{lifecycle.reporter_type}_POLICY" if lifecycle.reporter_type else "NON_HCP_POLICY",
            "created_at": lifecycle.created_at.isoformat() if lifecycle.created_at else None,
            "updated_at": lifecycle.updated_at.isoformat() if lifecycle.updated_at else None,
            "attempts": [self._attempt_to_dict(a) for a in attempts],
            "audit_log": [self._audit_to_dict(a) for a in audit_log]
        }
    
    def _attempt_to_dict(self, attempt: LifecycleAttempt) -> Dict[str, Any]:
        """Convert attempt model to dictionary."""
        return {
            "attempt_id": str(attempt.attempt_id),
            "attempt_number": attempt.attempt_number,
            "attempt_type": attempt.attempt_type,
            "channel": attempt.channel,
            "sent_to": attempt.sent_to,
            "questions_sent": attempt.questions_sent,
            "questions_count": attempt.questions_count or 0,
            "sent_at": attempt.sent_at.isoformat() if attempt.sent_at else None,
            "reminder_sent": attempt.reminder_sent or False,
            "reminder_sent_at": attempt.reminder_sent_at.isoformat() if attempt.reminder_sent_at else None,
            "response_received": attempt.response_received or False,
            "response_received_at": attempt.response_received_at.isoformat() if attempt.response_received_at else None,
            "response_type": attempt.response_type,
            "questions_answered": attempt.questions_answered or 0,
            "compliance_24h_met": attempt.compliance_24h_met if attempt.compliance_24h_met is not None else True
        }
    
    def _audit_to_dict(self, audit: LifecycleAuditLog) -> Dict[str, Any]:
        """Convert audit log model to dictionary."""
        return {
            "log_id": str(audit.log_id),
            "action_type": audit.action_type,
            "action_description": audit.action_description,
            "reason": audit.reason,
            "actor": audit.actor,
            "actor_type": audit.actor_type,
            "policy_applied": audit.policy_applied,
            "timestamp": audit.timestamp.isoformat() if audit.timestamp else None
        }
    
    def get_lifecycle_summary(self, lifecycle: FollowUpLifecycle) -> Dict[str, Any]:
        """Get a summary of lifecycle status."""
        return {
            "case_id": str(lifecycle.case_id),
            "reporter_type": lifecycle.reporter_type,
            "lifecycle_status": lifecycle.lifecycle_status,
            "attempt_count": lifecycle.attempt_count or 0,
            "max_attempts": lifecycle.max_attempts or 3,
            "response_status": lifecycle.response_status or "pending",
            "escalation_status": lifecycle.escalation_status or "none",
            "days_remaining": lifecycle.days_remaining,
            "completeness_score": lifecycle.completeness_score or 0.0,
            "dead_case_flag": lifecycle.dead_case_flag or False,
            "policy_applied": f"{lifecycle.reporter_type}_POLICY" if lifecycle.reporter_type else "NON_HCP_POLICY",
            "next_action": self._determine_next_action(lifecycle)
        }
    
    def _determine_next_action(self, lifecycle: FollowUpLifecycle) -> str:
        """Determine the next action needed."""
        status = lifecycle.lifecycle_status
        
        if status == "completed":
            return "NONE - Case complete"
        elif status == "dead_case":
            return "NONE - Case dead"
        elif status == "closed":
            return "NONE - Case closed"
        elif status == "escalated":
            return "AWAIT_HUMAN_REVIEW"
        
        is_due, _ = self.is_reminder_due(lifecycle)
        if is_due:
            return "SEND_REMINDER"
        
        needs_esc, _, _ = self.check_escalation_needed(lifecycle)
        if needs_esc:
            return "ESCALATE"
        
        is_dead, _ = self.check_dead_case(lifecycle)
        if is_dead:
            return "MARK_DEAD"
        
        if lifecycle.response_status == "pending":
            return "AWAIT_RESPONSE"
        elif lifecycle.response_status == "partial":
            return "SEND_FOLLOWUP"
        
        return "CONTINUE_MONITORING"
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get overview stats for all tracked lifecycles."""
        all_lifecycles = self.db.query(FollowUpLifecycle).all()
        
        total = len(all_lifecycles)
        
        if total == 0:
            return {
                "total_cases": 0,
                "by_status": {},
                "by_reporter_type": {},
                "escalated_count": 0,
                "dead_case_count": 0
            }
        
        by_status = {}
        by_reporter = {}
        escalated = 0
        dead_cases = 0
        
        for lc in all_lifecycles:
            status = lc.lifecycle_status or "unknown"
            reporter = lc.reporter_type or "unknown"
            
            by_status[status] = by_status.get(status, 0) + 1
            by_reporter[reporter] = by_reporter.get(reporter, 0) + 1
            
            if lc.escalation_status and lc.escalation_status not in ["none"]:
                escalated += 1
            
            if lc.dead_case_flag:
                dead_cases += 1
        
        return {
            "total_cases": total,
            "by_status": by_status,
            "by_reporter_type": by_reporter,
            "escalated_count": escalated,
            "dead_case_count": dead_cases
        }


def create_lifecycle_db_service(db: Session) -> LifecycleDBService:
    """Factory function to create lifecycle DB service."""
    return LifecycleDBService(db)
