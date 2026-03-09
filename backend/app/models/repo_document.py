"""
Repo Document Model — Global document repository (independent of cases).

Stores form templates (TAFU, Pregnancy, Custom) that can be reused across
any case. Questions are extracted on upload and stored permanently.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class RepoDocument(Base):
    __tablename__ = "repo_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String(500), nullable=False)
    form_type = Column(String(50), nullable=False)  # TAFU / PREGNANCY / CUSTOM
    file_name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    uploaded_by = Column(String(200), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Output of extract_checklist_items(), stored permanently
    extracted_questions = Column(JSONB, nullable=True)
    extraction_status = Column(String(20), default="PENDING", nullable=False)
    extraction_error = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_repo_documents_active", "is_active"),
        Index("ix_repo_documents_type_active", "form_type", "is_active"),
    )

    def __repr__(self):
        return (
            f"<RepoDocument id={self.id} name={self.display_name} "
            f"type={self.form_type} status={self.extraction_status}>"
        )
