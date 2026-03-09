"""
Case Schemas
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class MissingFieldBase(BaseModel):
    field_name: str
    field_category: Optional[str] = None
    safety_criticality: Optional[str] = None
    is_missing: bool = True
    should_follow_up: bool = True
    impact_explanation: Optional[str] = None

class MissingFieldCreate(MissingFieldBase):
    pass

class MissingField(MissingFieldBase):
    id: UUID
    case_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class CaseBase(BaseModel):
    primaryid: int
    patient_age: Optional[int] = None
    patient_sex: Optional[str] = None
    suspect_drug: str
    adverse_event: str
    drug_route: Optional[str] = None
    drug_dose: Optional[str] = None
    event_date: Optional[datetime] = None
    reporter_type: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    patient_age: Optional[int] = None
    patient_sex: Optional[str] = None
    drug_dose: Optional[str] = None
    event_date: Optional[datetime] = None
    case_status: Optional[str] = None

class Case(CaseBase):
    case_id: UUID
    seriousness_score: float
    data_completeness_score: float
    case_priority: Optional[str] = None
    case_status: str
    is_serious: bool
    requires_followup: bool
    intake_source: Optional[str] = "CSV"
    source_filename: Optional[str] = None
    # CIOMS Form-I fields
    patient_initials: Optional[str] = None
    indication: Optional[str] = None
    therapy_start: Optional[datetime] = None
    therapy_end: Optional[datetime] = None
    therapy_duration: Optional[int] = None
    dechallenge: Optional[str] = None
    rechallenge: Optional[str] = None
    concomitant_drugs: Optional[str] = None
    medical_history: Optional[str] = None
    report_type: Optional[str] = None
    reporter_email: Optional[str] = None
    reporter_phone: Optional[str] = None
    manufacturer_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    missing_fields: List[MissingField] = []

    class Config:
        from_attributes = True

class CaseList(BaseModel):
    total: int
    cases: List[Case]
    page: int
    page_size: int
