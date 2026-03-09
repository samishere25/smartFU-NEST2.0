"""
Case Document Model — Multiple documents per case.

Supports: CIOMS, TAFU, PREGNANCY, REVIEWER_NOTE, RESPONSE document types.
AECase table remains completely unchanged.
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class DocumentType(str, enum.Enum):
    """Allowed document types for a case."""
    CIOMS = "CIOMS"
    TAFU = "TAFU"
    PREGNANCY = "PREGNANCY"
    REVIEWER_NOTE = "REVIEWER_NOTE"
    RESPONSE = "RESPONSE"


class CaseDocument(Base):
    """
    A document attached to an AECase.

    One case can have many documents.
    Only CIOMS documents trigger extraction and AECase updates.
    All others are metadata-only storage.
    """
    __tablename__ = "case_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ae_cases.case_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type = Column(
        SAEnum(DocumentType, name="document_type_enum", create_type=True),
        nullable=False,
    )

    file_name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    uploaded_by = Column(String(200), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Extracted JSON from CIOMS documents; null for all other types
    extracted_json = Column(JSONB, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship back to AECase
    case = relationship("AECase", back_populates="documents")

    def __repr__(self):
        return (
            f"<CaseDocument id={self.id} case_id={self.case_id} "
            f"type={self.document_type} file={self.file_name}>"
        )
