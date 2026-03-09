"""
Regulatory Workflow Model
"""

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.base import Base


class RegulatoryWorkflow(Base):
    """Regulatory workflow triggered by signal escalation"""
    __tablename__ = "regulatory_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, default="IN_PROGRESS")
    report_type = Column(String(100), nullable=False, default="CIOMS_DRAFT")
    due_date = Column(DateTime, nullable=False)
    cioms_placeholder = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
