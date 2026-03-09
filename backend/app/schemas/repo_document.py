"""
Pydantic schemas for Global Document Repository.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RepoDocumentOut(BaseModel):
    id: UUID
    display_name: str
    form_type: str
    file_name: str
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    extraction_status: str
    extraction_error: Optional[str] = None
    is_active: bool
    description: Optional[str] = None
    questions_count: int = 0
    extracted_questions: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class RepoDocumentListItem(BaseModel):
    """Lightweight version without extracted_questions (for dropdown/list)."""
    id: UUID
    display_name: str
    form_type: str
    file_name: str
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    extraction_status: str
    is_active: bool
    description: Optional[str] = None
    questions_count: int = 0

    class Config:
        from_attributes = True


class RepoDocumentListResponse(BaseModel):
    total: int
    documents: List[RepoDocumentListItem]


class RepoDocumentQuestionsOut(BaseModel):
    id: UUID
    display_name: str
    form_type: str
    extracted_questions: List[Dict[str, Any]] = []
    extraction_status: str


class CiomsCombinedSendRequest(BaseModel):
    repo_doc_ids: List[UUID] = Field(default_factory=list)
    reviewer_notes: str = ""
    cioms_missing_fields: List[str] = Field(default_factory=list)
