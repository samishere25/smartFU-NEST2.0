"""
Adverse Event Case Models
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.base import Base

class AECase(Base):
    """Adverse Event Case"""
    __tablename__ = "ae_cases"
    
    case_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primaryid = Column(Integer, unique=True, nullable=False, index=True)
    receipt_date = Column(DateTime, default=datetime.utcnow)
    
    # Patient Information
    patient_age = Column(Integer, nullable=True)
    patient_sex = Column(String(10), nullable=True)
    patient_age_group = Column(String(20), nullable=True)
    
    # Drug Information
    suspect_drug = Column(String(500), nullable=False)
    drug_route = Column(String(100), nullable=True)
    drug_dose = Column(String(500), nullable=True)
    
    # Event Information
    adverse_event = Column(String(1000), nullable=False)
    event_date = Column(DateTime, nullable=True)
    event_outcome = Column(String(100), nullable=True)
    
    # Reporter Information
    reporter_type = Column(String(10), nullable=True)  # CN/HP/MD/LW/PH
    reporter_country = Column(String(5), nullable=True)
    
    # Assessment Scores
    seriousness_score = Column(Float, default=0.0)
    data_completeness_score = Column(Float, default=0.0)
    case_priority = Column(String(20), nullable=True)
    
    # Status
    case_status = Column(String(50), default='INITIAL_RECEIVED')
    is_serious = Column(Boolean, default=False)
    requires_followup = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    missing_fields = relationship("MissingField", back_populates="case", cascade="all, delete-orphan")
    followup_decisions = relationship("FollowUpDecision", back_populates="case")
    followup_attempts = relationship("FollowUpAttempt", back_populates="case")


class MissingField(Base):
    """Missing Field Tracking"""
    __tablename__ = "missing_fields"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'))
    
    field_name = Column(String(100), nullable=False)
    field_category = Column(String(50))  # PATIENT, DRUG, EVENT
    
    is_missing = Column(Boolean, default=True)
    is_unclear = Column(Boolean, default=False)
    is_inconsistent = Column(Boolean, default=False)
    
    safety_criticality = Column(String(20))  # CRITICAL/HIGH/MEDIUM/LOW
    regulatory_requirement = Column(Boolean, default=False)
    
    should_follow_up = Column(Boolean, default=True)
    followup_priority = Column(Integer)
    question_value_score = Column(Float)
    
    missing_reason = Column(Text)
    impact_explanation = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("AECase", back_populates="missing_fields")
