"""
Models package - imports all models for SQLAlchemy relationship resolution
"""

from app.models.user import User
from app.models.case import AECase, MissingField
from app.models.case_document import CaseDocument, DocumentType
from app.models.followup import (
    FollowUpAttempt,
    FollowUpDecision,
    FollowUpResponse,
    FieldUpdateHistory,
    CaseConfidenceHistory,
    AdaptiveLoopSession
)
from app.models.signal import SafetySignal
from app.models.audit import AuditLog
from app.models.regulatory import RegulatoryWorkflow
from app.models.pv_audit_trail import PVAuditTrail
from app.models.repo_document import RepoDocument
# Feature-4: Lifecycle Tracking
from app.models.lifecycle_tracker import (
    FollowUpLifecycle,
    LifecycleAttempt,
    LifecycleAuditLog,
    ReporterPolicy
)

__all__ = [
    "User",
    "AECase",
    "MissingField",
    "CaseDocument",
    "DocumentType",
    "FollowUpAttempt",
    "FollowUpDecision",
    "FollowUpResponse",
    "FieldUpdateHistory",
    "CaseConfidenceHistory",
    "AdaptiveLoopSession",
    "SafetySignal",
    "AuditLog",
    "RegulatoryWorkflow",
    # Feature-4: Lifecycle Tracking
    "FollowUpLifecycle",
    "LifecycleAttempt",
    "LifecycleAuditLog",
    "ReporterPolicy",
    "PVAuditTrail",
    "RepoDocument",
]
