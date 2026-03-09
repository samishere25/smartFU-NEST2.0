"""
Follow-Up Lifecycle Tracking Models
====================================

Feature-4: Complete lifecycle tracking for adverse event follow-ups.

Tracks:
- Attempt counting
- Reminder scheduling (24h compliance)
- Escalation state
- Regulatory deadline awareness (7/15 day)
- Dead-case classification
- HCP vs Non-HCP policy differentiation
- Audit logging

This is the operational spine of the system.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum

from app.db.base import Base


# ============================================================================
# ENUMS
# ============================================================================

class ResponseStatus(str, enum.Enum):
    """Response status from reporter"""
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETE = "complete"
    NO_RESPONSE = "no_response"


class EscalationStatus(str, enum.Enum):
    """Escalation state"""
    NONE = "none"
    FLAGGED = "flagged"
    URGENT = "urgent"
    ESCALATED_TO_REVIEWER = "escalated_to_reviewer"
    ESCALATED_TO_MEDICAL = "escalated_to_medical"


class SeriousnessLevel(str, enum.Enum):
    """Case seriousness level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReporterType(str, enum.Enum):
    """Reporter type for policy differentiation"""
    HCP = "HCP"  # Health Care Professional (Doctor, Nurse, Pharmacist)
    NON_HCP = "NON_HCP"  # Patient, Consumer, Lawyer, Other


class LifecycleStatus(str, enum.Enum):
    """Overall lifecycle status"""
    ACTIVE = "active"
    AWAITING_RESPONSE = "awaiting_response"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    DEAD_CASE = "dead_case"
    CLOSED = "closed"


# ============================================================================
# MAIN LIFECYCLE TRACKING MODEL
# ============================================================================

class FollowUpLifecycle(Base):
    """
    Main lifecycle tracking table for each case.
    
    This is the BACKBONE of the tracking system.
    One record per case.
    """
    __tablename__ = "followup_lifecycle"
    
    # Primary Key
    lifecycle_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    
    # ==================== REPORTER SEGMENTATION ====================
    reporter_type = Column(String(20), default="NON_HCP")  # HCP or NON_HCP
    reporter_subtype = Column(String(50), nullable=True)  # MD, HP, PT, CN, etc.
    
    # ==================== ATTEMPT LIFECYCLE ====================
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)  # 4 for HCP, 3 for Non-HCP
    last_attempt_at = Column(DateTime, nullable=True)
    next_reminder_due = Column(DateTime, nullable=True)
    reminder_interval_hours = Column(Integer, default=24)  # 24h compliance rule
    
    # ==================== RESPONSE TRACKING ====================
    response_status = Column(String(20), default="pending")  # pending/partial/complete/no_response
    last_response_at = Column(DateTime, nullable=True)
    total_questions_sent = Column(Integer, default=0)
    total_questions_answered = Column(Integer, default=0)
    
    # ==================== QUESTION LIMITS (HCP vs Non-HCP) ====================
    questions_per_round = Column(Integer, default=3)  # 5 for HCP, 2 for Non-HCP
    
    # ==================== ESCALATION ====================
    escalation_status = Column(String(50), default="none")  # none/flagged/urgent/escalated_to_reviewer/escalated_to_medical
    escalation_reason = Column(Text, nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    escalated_to = Column(String(100), nullable=True)  # User ID or team name
    
    # ==================== REGULATORY DEADLINES ====================
    seriousness_level = Column(String(20), default="medium")  # low/medium/high/critical
    regulatory_deadline = Column(DateTime, nullable=False)
    days_remaining = Column(Integer, nullable=True)
    deadline_type = Column(String(20), default="15_day")  # 7_day or 15_day
    
    # ==================== COMPLETION METRICS ====================
    completeness_score = Column(Float, default=0.0)
    safety_confidence_score = Column(Float, default=0.0)
    target_completeness = Column(Float, default=0.85)  # Policy threshold
    mandatory_fields_complete = Column(Boolean, default=False)
    
    # ==================== CLOSURE ====================
    dead_case_flag = Column(Boolean, default=False)
    closure_reason = Column(Text, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(100), nullable=True)  # system/user_id
    
    # ==================== LIFECYCLE STATUS ====================
    lifecycle_status = Column(String(30), default="active")  # active/awaiting_response/escalated/completed/dead_case/closed
    
    # ==================== METADATA ====================
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ==================== RELATIONSHIPS ====================
    case = relationship("AECase", backref="lifecycle")
    audit_logs = relationship("LifecycleAuditLog", back_populates="lifecycle", cascade="all, delete-orphan")
    attempts = relationship("LifecycleAttempt", back_populates="lifecycle", cascade="all, delete-orphan")


# ============================================================================
# LIFECYCLE ATTEMPT TRACKING
# ============================================================================

class LifecycleAttempt(Base):
    """
    Track each individual follow-up attempt.
    
    Maintains history of all contact attempts.
    """
    __tablename__ = "lifecycle_attempts"
    
    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lifecycle_id = Column(UUID(as_uuid=True), ForeignKey('followup_lifecycle.lifecycle_id', ondelete='CASCADE'), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Attempt details
    attempt_number = Column(Integer, nullable=False)
    attempt_type = Column(String(50), default="followup")  # initial/followup/reminder/escalation
    
    # Channel used
    channel = Column(String(50), nullable=True)  # EMAIL/WHATSAPP/PHONE/SMS
    sent_to = Column(String(255), nullable=True)
    
    # Questions sent
    questions_sent = Column(JSON, nullable=True)
    questions_count = Column(Integer, default=0)
    
    # Timing
    sent_at = Column(DateTime, default=datetime.utcnow)
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime, nullable=True)
    
    # Response
    response_received = Column(Boolean, default=False)
    response_received_at = Column(DateTime, nullable=True)
    response_type = Column(String(30), nullable=True)  # full/partial/none
    questions_answered = Column(Integer, default=0)
    
    # Compliance
    compliance_24h_met = Column(Boolean, default=True)  # Was 24h rule followed?
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lifecycle = relationship("FollowUpLifecycle", back_populates="attempts")


# ============================================================================
# AUDIT LOG
# ============================================================================

class LifecycleAuditLog(Base):
    """
    Audit trail for all lifecycle actions.
    
    CRITICAL for compliance - every action must be logged.
    """
    __tablename__ = "lifecycle_audit_log"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lifecycle_id = Column(UUID(as_uuid=True), ForeignKey('followup_lifecycle.lifecycle_id', ondelete='CASCADE'), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(100), nullable=False)
    # Actions: CASE_CREATED, FOLLOWUP_SENT, REMINDER_SENT, RESPONSE_RECEIVED, 
    #          ESCALATION_FLAGGED, ESCALATION_TRIGGERED, DEADLINE_WARNING,
    #          DEAD_CASE_MARKED, CASE_CLOSED, POLICY_APPLIED
    
    action_description = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    
    # Actor
    actor = Column(String(100), default="system")  # system/user_id
    actor_type = Column(String(50), default="system")  # system/human/policy_engine
    
    # State snapshot
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    
    # Policy reference
    policy_applied = Column(String(100), nullable=True)  # HCP_POLICY/NON_HCP_POLICY
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    lifecycle = relationship("FollowUpLifecycle", back_populates="audit_logs")


# ============================================================================
# REPORTER POLICY CONFIGURATION
# ============================================================================

class ReporterPolicy(Base):
    """
    Policy configuration for HCP vs Non-HCP.
    
    Allows configurable rules without code changes.
    """
    __tablename__ = "reporter_policies"
    
    policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Policy name
    policy_name = Column(String(50), unique=True, nullable=False)  # HCP_POLICY, NON_HCP_POLICY
    reporter_type = Column(String(20), nullable=False)  # HCP or NON_HCP
    
    # Attempt limits
    max_attempts = Column(Integer, default=3)
    reminder_interval_hours = Column(Integer, default=24)
    
    # Question limits
    questions_per_round = Column(Integer, default=3)
    max_questions_total = Column(Integer, default=15)
    
    # Escalation rules
    escalation_after_attempts = Column(Integer, default=3)
    escalate_to = Column(String(100), default="supervisor")  # supervisor/medical_team
    allow_auto_dead_case = Column(Boolean, default=True)
    
    # Deadline rules
    deadline_warning_days = Column(Integer, default=2)
    
    # Active flag
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# HELPER: Add relationship to AECase
# ============================================================================
# Note: Add this to app/models/case.py:
# lifecycle = relationship("FollowUpLifecycle", back_populates="case", uselist=False)
