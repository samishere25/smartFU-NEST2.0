"""
Follow-Up Models
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.base import Base

class FollowUpDecision(Base):
    """Follow-Up Decision"""
    __tablename__ = "followup_decisions"
    
    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'))
    
    decision_type = Column(String(50), nullable=False)  # PROCEED/DEFER/SKIP/ESCALATE
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
    
    # Relationships
    case = relationship("AECase", back_populates="followup_decisions")


class FollowUpAttempt(Base):
    """Follow-Up Attempt"""
    __tablename__ = "followup_attempts"
    
    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'))
    decision_id = Column(UUID(as_uuid=True), ForeignKey('followup_decisions.decision_id'))
    
    attempt_number = Column(Integer, nullable=False)
    sent_at = Column(DateTime, nullable=False)
    channel = Column(String(50), nullable=False)
    
    recipient_email = Column(String(255))
    secure_token = Column(String(500), unique=True)
    
    questions_sent = Column(Integer, nullable=False)
    fields_requested = Column(JSON, nullable=False)
    
    response_status = Column(String(50), default='SENT')
    responded_at = Column(DateTime)
    response_time_hours = Column(Integer)
    
    questions_answered = Column(Integer, default=0)
    data_quality_score = Column(Float)
    
    stop_followup = Column(Boolean, default=False)
    stop_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("AECase", back_populates="followup_attempts")
    responses = relationship("FollowUpResponse", back_populates="attempt")


class FollowUpResponse(Base):
    """Follow-Up Response"""
    __tablename__ = "followup_responses"
    
    response_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey('followup_attempts.attempt_id', ondelete='CASCADE'))
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'))
    
    field_name = Column(String(100), nullable=False)
    field_value = Column(Text)
    value_type = Column(String(50))
    
    is_complete = Column(Boolean, default=False)
    is_validated = Column(Boolean, default=False)
    
    needs_clarification = Column(Boolean, default=False)
    ai_extracted_value = Column(Text)
    extraction_confidence = Column(Float)
    
    responded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    attempt = relationship("FollowUpAttempt", back_populates="responses")
