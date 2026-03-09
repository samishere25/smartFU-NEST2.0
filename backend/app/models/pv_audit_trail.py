"""
Pharmacovigilance Audit Trail Model
====================================

Immutable, append-only audit trail for regulatory compliance.
Captures every critical action in the PV lifecycle.

Designed for: FDA 21 CFR Part 11, EMA GVP, MHRA compliance.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.base import Base


class PVAuditTrail(Base):
    """
    Immutable pharmacovigilance audit trail.

    No UPDATE or DELETE operations are permitted on this table.
    Every entry is append-only for regulatory inspection readiness.
    """
    __tablename__ = "pv_audit_trail"

    # Primary Key
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Case linkage (nullable for system-wide events like signal detection)
    case_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Timestamp (UTC, indexed for time-range queries)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Actor identification
    actor_type = Column(String(20), nullable=False)  # AI / HUMAN / SYSTEM / REPORTER
    actor_id = Column(String(200), nullable=True)  # user_id, system name, or null for AI

    # Action classification
    action_type = Column(String(100), nullable=False, index=True)
    # Supported action_types:
    # CASE_CREATED, CIOMS_PARSED, FIELDS_EXTRACTED, AI_RISK_DECISION,
    # AI_FOLLOWUP_DECISION, HUMAN_OVERRIDE, FOLLOWUP_SENT, RESPONSE_RECEIVED,
    # REVIEWER_NOTE_ADDED, REGULATORY_ESCALATION, SIGNAL_DETECTED,
    # SIGNAL_REVIEWED, SIGNAL_PRIORITY_CHANGED, SIGNAL_FALSE_POSITIVE,
    # LIFECYCLE_STAGE_CHANGE, CASE_CLOSED, CASE_REOPENED,
    # REGULATORY_WORKFLOW_CREATED, SIGNAL_SNAPSHOT_FROZEN

    # Value tracking (before/after for changes)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    # Decision metadata snapshot (full context at time of action)
    decision_metadata = Column(JSON, nullable=True)

    # AI-specific fields
    model_version = Column(String(100), nullable=True)  # e.g., "mistral-large-latest"
    confidence_score = Column(Float, nullable=True)

    # Communication-specific fields
    channel = Column(String(50), nullable=True)  # EMAIL / PHONE / WHATSAPP / SMS

    # Signal-specific fields
    signal_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Human-readable description
    description = Column(Text, nullable=False)

    # Regulatory flags
    regulatory_impact = Column(Boolean, default=False)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_pv_audit_case_action', 'case_id', 'action_type'),
        Index('ix_pv_audit_case_time', 'case_id', 'timestamp'),
        Index('ix_pv_audit_actor_time', 'actor_type', 'timestamp'),
        Index('ix_pv_audit_signal_action', 'signal_id', 'action_type'),
    )
