"""
Follow-up Tracking Models
Track the complete lifecycle of follow-up attempts
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class FollowUpDecision(Base):
    """Follow-Up Decision - tracks the decision to follow up"""
    __tablename__ = "followup_decisions"
    
    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'))
    
    decision_type = Column(String(50), nullable=False)
    decision_reason = Column(Text, nullable=False)
    
    agent_name = Column(String(100))
    confidence_score = Column(Float)
    
    predicted_response_probability = Column(Float)
    optimal_timing_hours = Column(Integer)
    recommended_channel = Column(String(50))
    
    case_risk_level = Column(String(20))
    escalation_required = Column(Boolean, default=False)
    
    human_override = Column(Boolean, default=False)
    override_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class FollowUpAttempt(Base):
    """Track each follow-up attempt for a case"""
    __tablename__ = "followup_attempts"
    
    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("ae_cases.case_id"), nullable=False, index=True)
    decision_id = Column(UUID(as_uuid=True), ForeignKey('followup_decisions.decision_id'), nullable=True)
    
    # Iteration tracking
    iteration_number = Column(Integer, nullable=False, default=1)
    attempt_number = Column(Integer, nullable=False, default=1)  # Alias for compatibility
    
    # State at time of attempt
    safety_confidence = Column(Float, nullable=True)  # 0.0-1.0
    data_completeness = Column(Float, nullable=True)  # 0.0-1.0
    risk_score = Column(Float, nullable=True)
    response_probability = Column(Float, nullable=True)
    
    # Questions sent
    questions_sent = Column(JSON, nullable=True)  # List of questions or count - NULLABLE to avoid type issues
    questions_count = Column(Integer, nullable=True)
    fields_requested = Column(JSON, nullable=True)  # For compatibility
    
    # Communication details
    channel = Column(String(50), nullable=True)
    sent_method = Column(String(50), nullable=True)  # email/portal/api
    sent_to = Column(String(255), nullable=True)  # reporter email/id
    recipient_email = Column(String(255), nullable=True)  # Alias
    secure_token = Column(String(500), unique=True, nullable=True)
    
    # Decision made
    decision = Column(String(50), nullable=True)  # PROCEED/DEFER/SKIP/ESCALATE
    reasoning = Column(Text, nullable=True)
    
    # Attempt metadata
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Response tracking
    response_received = Column(Boolean, default=False)
    response_status = Column(String(50), default="SENT")  # SENT/RESPONDED/NO_RESPONSE
    response_received_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)  # Alias
    response_data = Column(JSON, nullable=True)  # Answers received
    response_time_hours = Column(Float, nullable=True)
    questions_answered = Column(Integer, default=0)
    data_quality_score = Column(Float, nullable=True)
    
    # Outcome
    status = Column(String(50), default="PENDING")  # PENDING/RESPONDED/NO_RESPONSE/EXPIRED
    information_gained = Column(Float, nullable=True)  # How much did we learn?
    stop_followup = Column(Boolean, default=False)
    stop_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("AECase", back_populates="followup_attempts")
    responses = relationship("FollowUpResponse", back_populates="attempt")


class FollowUpResponse(Base):
    """Follow-Up Response - individual field responses from reporters.

    Every answer received via any channel (EMAIL / PHONE / WHATSAPP / WEB)
    is persisted here so the Novartis Review Dashboard can display a full
    response history with version tracking.
    """
    __tablename__ = "followup_responses"
    
    response_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey('followup_attempts.attempt_id', ondelete='CASCADE'), nullable=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Question context
    question_id = Column(String(200), nullable=True)          # stable id from question payload
    question_text = Column(Text, nullable=True)               # original question text sent
    field_name = Column(String(100), nullable=False)           # CIOMS field targeted
    
    # Reporter answer
    response_text = Column(Text, nullable=True)                # raw answer text from reporter
    field_value = Column(Text, nullable=True)                  # normalised / mapped value saved to case
    previous_value = Column(Text, nullable=True)               # value of the field BEFORE this update (version history)
    value_type = Column(String(50), nullable=True)             # e.g. STRING, DATE, INTEGER
    
    # Channel & source
    channel = Column(String(50), nullable=True)                # EMAIL / PHONE / WHATSAPP / WEB
    attempt_number = Column(Integer, nullable=True)            # which follow-up round (1-based)
    
    # Validation flags
    is_complete = Column(Boolean, default=False)
    is_validated = Column(Boolean, default=False)
    needs_clarification = Column(Boolean, default=False)
    processed = Column(Boolean, default=True)                  # has this been applied to the case?
    
    # AI extraction (for voice / free-text)
    ai_extracted_value = Column(Text, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    
    # File attachment (if reporter sent a file)
    response_file_url = Column(String(500), nullable=True)
    
    # Timestamps
    responded_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    attempt = relationship("FollowUpAttempt", back_populates="responses")


class FieldUpdateHistory(Base):
    """Tracks every change to a case field, providing old→new version history.

    Created by ResponseProcessor whenever a reporter answer updates an AECase column.
    The Novartis Review Dashboard uses this to show Updated Case Fields with provenance.
    """
    __tablename__ = "field_update_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False, index=True)
    response_id = Column(UUID(as_uuid=True), ForeignKey('followup_responses.response_id', ondelete='SET NULL'), nullable=True)

    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)  # EMAIL / PHONE / WHATSAPP / WEB / MANUAL
    changed_by = Column(String(200), nullable=True)  # 'reporter' or user email
    changed_at = Column(DateTime, default=datetime.utcnow)


class CaseConfidenceHistory(Base):
    """Track confidence evolution over time"""
    __tablename__ = "case_confidence_history"
    
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("ae_cases.case_id"), nullable=False, index=True)
    
    # Confidence metrics
    safety_confidence = Column(Float, nullable=False)
    data_completeness = Column(Float, nullable=False)
    risk_assessment_confidence = Column(Float, nullable=False)
    overall_confidence = Column(Float, nullable=False)
    
    # What changed
    trigger_event = Column(String(100))  # initial/response_received/manual_update
    fields_updated = Column(JSON)  # Which fields were filled
    information_gain = Column(Float)  # How much confidence increased
    
    # Should we continue?
    continue_followup = Column(Boolean, nullable=False)
    reason = Column(Text)
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    case = relationship("AECase", back_populates="confidence_history")


class AdaptiveLoopSession(Base):
    """Track entire adaptive loop session for a case"""
    __tablename__ = "adaptive_loop_sessions"
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("ae_cases.case_id"), nullable=False, index=True)
    
    # Session metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_iterations = Column(Integer, default=0)
    
    # Initial state
    initial_confidence = Column(Float, nullable=False)
    initial_completeness = Column(Float, nullable=False)
    target_confidence = Column(Float, default=0.85)  # Goal threshold
    
    # Final state
    final_confidence = Column(Float, nullable=True)
    final_completeness = Column(Float, nullable=True)
    confidence_gain = Column(Float, nullable=True)
    
    # Convergence
    converged = Column(Boolean, default=False)
    convergence_reason = Column(String(100))  # threshold_reached/max_iterations/no_response/diminishing_returns
    
    # Outcomes
    questions_sent_total = Column(Integer, default=0)
    responses_received = Column(Integer, default=0)
    response_rate = Column(Float, nullable=True)
    
    # Efficiency metrics
    information_per_question = Column(Float, nullable=True)
    cost_benefit_ratio = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), default="ACTIVE")  # ACTIVE/COMPLETED/ABANDONED
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("AECase", back_populates="adaptive_sessions")


# Add relationships to AECase model
# In app/models/case.py, add these relationships:
"""
from sqlalchemy.orm import relationship

class AECase(Base):
    # ... existing fields ...
    
    # Add these relationships:
    followup_attempts = relationship("FollowUpAttempt", back_populates="case", cascade="all, delete-orphan")
    confidence_history = relationship("CaseConfidenceHistory", back_populates="case", cascade="all, delete-orphan")
    adaptive_sessions = relationship("AdaptiveLoopSession", back_populates="case", cascade="all, delete-orphan")
"""