"""
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
