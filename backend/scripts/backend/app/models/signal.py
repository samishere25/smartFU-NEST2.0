"""
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
