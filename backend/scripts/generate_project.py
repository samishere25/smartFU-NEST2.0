#!/usr/bin/env python3
"""
SmartFU Project Generator
This script generates all remaining project files programmatically
Run this after downloading the initial structure
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

def create_file(filepath: str, content: str):
    """Create a file with content"""
    file_path = BASE_DIR / filepath
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(content)
    print(f"✅ Created: {filepath}")

# =============================================
# DATABASE BASE AND MODELS
# =============================================

create_file("backend/app/db/base.py", '''"""
SQLAlchemy base class
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here for Alembic
from app.models.user import User
from app.models.case import AECase, MissingField
from app.models.followup import FollowUpDecision, FollowUpAttempt, FollowUpResponse
from app.models.audit import AuditLog
from app.models.signal import SafetySignal
''')

create_file("backend/app/models/case.py", '''"""
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
''')

create_file("backend/app/models/user.py", '''"""
User Model
"""

from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.base import Base

class User(Base):
    """User Model"""
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(500), nullable=False)
    
    # Profile
    full_name = Column(String(200))
    role = Column(String(50), nullable=False)  # PV_SPECIALIST, SAFETY_OFFICER, ADMIN
    department = Column(String(100))
    organization = Column(String(200))
    
    # Permissions
    permissions = Column(JSON, default=list)
    can_approve_high_risk = Column(Boolean, default=False)
    
    # Security
    mfa_enabled = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
''')

create_file("backend/app/models/followup.py", '''"""
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
''')

create_file("backend/app/models/audit.py", '''"""
Audit Log Model
"""

from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
import uuid
from datetime import datetime

from app.db.base import Base

class AuditLog(Base):
    """Audit Log"""
    __tablename__ = "audit_logs"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    activity_type = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    
    user_id = Column(String(100))
    user_role = Column(String(50))
    ip_address = Column(INET)
    
    before_state = Column(JSON)
    after_state = Column(JSON)
    change_description = Column(Text)
    
    regulatory_impact = Column(Boolean, default=False)
    gdpr_relevant = Column(Boolean, default=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
''')

create_file("backend/app/models/signal.py", '''"""
Safety Signal Model
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.base import Base

class SafetySignal(Base):
    """Safety Signal"""
    __tablename__ = "safety_signals"
    
    signal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    drug_name = Column(String(500))
    adverse_event = Column(String(1000))
    signal_type = Column(String(50))  # EMERGING/CONFIRMED/DISMISSED
    
    case_count = Column(Integer)
    reporting_rate = Column(Float)
    proportional_reporting_ratio = Column(Float)
    
    temporal_pattern = Column(Text)
    demographic_pattern = Column(Text)
    
    signal_strength = Column(String(20))  # STRONG/MODERATE/WEAK
    clinical_significance = Column(Text)
    
    signal_status = Column(String(50), default='DETECTED')
    detected_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String(100))
''')

print("\\n✅ All database models created!")
print("\\nNext steps:")
print("1. Run: pip install -r backend/requirements.txt")
print("2. Start Docker: docker-compose up -d postgres redis")
print("3. Run migrations: cd backend && alembic upgrade head")
print("4. Load data: python scripts/load_data.py")
print("5. Train models: python scripts/train_models.py")
print("6. Start server: uvicorn app.main:app --reload")
