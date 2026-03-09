"""
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
