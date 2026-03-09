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
    reporter_type = Column(String(10), nullable=True)
    reporter_country = Column(String(5), nullable=True)
    
    # Assessment Scores
    seriousness_score = Column(Float, default=0.0)
    data_completeness_score = Column(Float, default=0.0)
    case_priority = Column(String(20), nullable=True)
    
    # Status
    case_status = Column(String(50), default='INITIAL_RECEIVED')
    is_serious = Column(Boolean, default=False)
    requires_followup = Column(Boolean, default=True)
    
    # Feature 7: Human Oversight
    human_reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=True)
    priority_score = Column(String(20), nullable=True)
    
    # Intake source tracking
    intake_source = Column(String(20), default='CSV')  # CSV, PDF, MANUAL
    source_filename = Column(String(500), nullable=True)  # original filename for PDF uploads

    # CIOMS Form-I fields (nullable — populated only for CIOMS PDF uploads)
    patient_initials = Column(String(20), nullable=True)
    indication = Column(String(500), nullable=True)
    therapy_start = Column(DateTime, nullable=True)
    therapy_end = Column(DateTime, nullable=True)
    therapy_duration = Column(Integer, nullable=True)  # days
    dechallenge = Column(String(50), nullable=True)
    rechallenge = Column(String(50), nullable=True)
    concomitant_drugs = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=True)
    reporter_email = Column(String(200), nullable=True)
    reporter_phone = Column(String(50), nullable=True)
    manufacturer_name = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    missing_fields = relationship("MissingField", back_populates="case", cascade="all, delete-orphan")
    followup_attempts = relationship("FollowUpAttempt", back_populates="case", cascade="all, delete-orphan")
    confidence_history = relationship("CaseConfidenceHistory", back_populates="case", cascade="all, delete-orphan")
    adaptive_sessions = relationship("AdaptiveLoopSession", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("CaseDocument", back_populates="case", cascade="all, delete-orphan")


class MissingField(Base):
    """Missing Field Tracking"""
    __tablename__ = "missing_fields"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('ae_cases.case_id', ondelete='CASCADE'))
    
    field_name = Column(String(100), nullable=False)
    field_category = Column(String(50))
    
    is_missing = Column(Boolean, default=True)
    is_unclear = Column(Boolean, default=False)
    is_inconsistent = Column(Boolean, default=False)
    
    safety_criticality = Column(String(20))
    regulatory_requirement = Column(Boolean, default=False)
    
    should_follow_up = Column(Boolean, default=True)
    followup_priority = Column(Integer)
    question_value_score = Column(Float)
    
    missing_reason = Column(Text)
    impact_explanation = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("AECase", back_populates="missing_fields")
