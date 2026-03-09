"""
Regulatory Workflow Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RegulatoryStartRequest(BaseModel):
    signalId: str


class RegulatoryWorkflowResponse(BaseModel):
    id: str
    signal_id: str
    status: str
    report_type: str
    due_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True
