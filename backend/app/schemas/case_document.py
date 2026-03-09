"""
Pydantic schemas for the CaseDocument API.
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class CaseDocumentOut(BaseModel):
    """Response schema for a single CaseDocument."""
    id: UUID
    case_id: UUID
    document_type: str
    file_name: str
    file_path: str
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    extracted_json: Optional[Any] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class CaseDocumentListOut(BaseModel):
    """Response schema for listing documents."""
    total: int
    documents: List[CaseDocumentOut]


class CombinedFollowUpOut(BaseModel):
    """Response schema for the consolidated follow-up builder."""
    case_id: str
    missing_questions: List[Any]
    reviewer_questions: List[Any]
    attachments: List[Any]
