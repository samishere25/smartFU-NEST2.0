"""
Follow-Up Schemas
Pydantic models for API request/response validation
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class FollowUpDecisionBase(BaseModel):
    decision_type: str
    decision_reason: str
    confidence_score: Optional[float] = None
    predicted_response_probability: Optional[float] = None
    case_risk_level: Optional[str] = None


class FollowUpDecisionCreate(FollowUpDecisionBase):
    case_id: UUID


class FollowUpDecision(FollowUpDecisionBase):
    decision_id: UUID
    case_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class FollowUpAttemptBase(BaseModel):
    attempt_number: int
    channel: str
    questions_sent: int
    fields_requested: List[str]


class FollowUpAttemptCreate(FollowUpAttemptBase):
    case_id: UUID
    decision_id: Optional[UUID] = None
    recipient_email: Optional[str] = None


class FollowUpAttempt(FollowUpAttemptBase):
    attempt_id: UUID
    case_id: UUID
    sent_at: datetime
    response_status: str
    questions_answered: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class FollowUpResponseBase(BaseModel):
    field_name: str
    field_value: Optional[str] = None


class FollowUpResponseCreate(FollowUpResponseBase):
    attempt_id: UUID
    case_id: UUID


class FollowUpResponse(FollowUpResponseBase):
    response_id: UUID
    is_complete: bool
    is_validated: bool
    responded_at: datetime
    
    class Config:
        from_attributes = True