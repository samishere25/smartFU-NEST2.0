"""
Case Service - Business Logic
"""

from sqlalchemy.orm import Session
from typing import List, Dict
import pandas as pd
from uuid import UUID

from app.models.case import AECase, MissingField
from app.schemas.case import CaseCreate

class CaseService:
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def _truncate_fields(case_data: Dict) -> Dict:
        """Truncate string fields to match DB column max lengths."""
        _MAX = {
            "suspect_drug": 500, "adverse_event": 1000, "reporter_type": 10,
            "reporter_country": 5, "drug_dose": 500, "drug_route": 100,
            "event_outcome": 100, "patient_sex": 10, "patient_age_group": 20,
            "case_priority": 20, "case_status": 50, "risk_level": 20,
            "priority_score": 20, "intake_source": 20, "source_filename": 500,
            "patient_initials": 20, "indication": 500, "dechallenge": 50,
            "rechallenge": 50, "report_type": 50, "reporter_email": 200,
            "reporter_phone": 50, "manufacturer_name": 500, "reviewed_by": 100,
        }
        for field, max_len in _MAX.items():
            val = case_data.get(field)
            if isinstance(val, str) and len(val) > max_len:
                case_data[field] = val[:max_len]
        return case_data

    async def create_case(self, case_data: Dict) -> AECase:
        """Create a new case"""
        case_data = self._truncate_fields(case_data)
        case = AECase(**case_data)
        
        # Analyze missing fields
        missing_fields = self._identify_missing_fields(case_data)
        
        self.db.add(case)
        self.db.flush()
        
        for field in missing_fields:
            field.case_id = case.case_id
            self.db.add(field)
        
        # Calculate scores
        case.data_completeness_score = self._calculate_completeness(case_data)
        
        self.db.commit()
        self.db.refresh(case)

        # ── Audit: CASE_CREATED ──
        try:
            from app.services.audit_service import AuditService
            AuditService.log_case_created(
                self.db,
                case_id=case.case_id,
                intake_source=case_data.get("intake_source", "CSV"),
                primaryid=case_data.get("primaryid"),
                suspect_drug=case_data.get("suspect_drug"),
                adverse_event=case_data.get("adverse_event"),
            )
        except Exception:
            pass  # Don't fail case creation if audit logging fails

        return case
    
    async def bulk_upload_csv(self, df: pd.DataFrame) -> Dict:
        """Bulk upload cases from DataFrame"""
        results = {
            "total": len(df),
            "created": 0,
            "failed": 0,
            "errors": []
        }
        
        for idx, row in df.iterrows():
            try:
                case_data = {
                    "primaryid": int(row['primaryid']),
                    "patient_age": int(row['age']) if pd.notna(row['age']) else None,
                    "patient_sex": row['sex'] if pd.notna(row['sex']) else None,
                    "suspect_drug": row['suspect_drug'],
                    "adverse_event": row['adverse_event'],
                    "drug_route": row['route'] if pd.notna(row['route']) else None,
                    "drug_dose": row['dose_vbm'] if pd.notna(row['dose_vbm']) else None,
                    "reporter_type": row['occp_cod'] if pd.notna(row['occp_cod']) else None,
                    "case_status": "INITIAL_RECEIVED"
                }
                
                await self.create_case(case_data)
                results["created"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "row": idx,
                    "error": str(e)
                })
        
        return results

    async def bulk_upload_xml(self, cases: list) -> Dict:
        """Bulk upload cases parsed from an XML file"""
        results = {
            "total": len(cases),
            "created": 0,
            "failed": 0,
            "errors": []
        }

        for idx, case_data in enumerate(cases):
            try:
                # Auto-assign primaryid if missing
                if not case_data.get("primaryid"):
                    import random
                    case_data["primaryid"] = random.randint(900_000_000, 999_999_999)

                await self.create_case(case_data)
                results["created"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"row": idx, "error": str(e)})

        return results

    def _identify_missing_fields(self, case_data: Dict) -> List[MissingField]:
        """Identify missing critical fields"""
        missing = []
        
        critical_fields = {
            "patient_age": ("PATIENT", "HIGH"),
            "event_date": ("EVENT", "CRITICAL"),
            "drug_dose": ("DRUG", "CRITICAL"),
            "patient_sex": ("PATIENT", "MEDIUM"),
            "drug_route": ("DRUG", "MEDIUM"),
            "patient_initials": ("PATIENT", "CRITICAL"),
            "reporter_type": ("REPORTER", "HIGH"),
        }
        
        for field_name, (category, criticality) in critical_fields.items():
            if not case_data.get(field_name):
                missing.append(MissingField(
                    field_name=field_name,
                    field_category=category,
                    safety_criticality=criticality,
                    is_missing=True,
                    should_follow_up=True
                ))
        
        return missing
    
    def _calculate_completeness(self, case_data: Dict) -> float:
        """Calculate data completeness score"""
        required_fields = [
            "patient_age", "patient_sex", "drug_dose",
            "drug_route", "event_date", "patient_initials",
            "reporter_type",
        ]
        
        present = sum(1 for field in required_fields if case_data.get(field))
        return present / len(required_fields)
