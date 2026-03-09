"""
User Model
"""

from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer
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
    must_change_password = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
