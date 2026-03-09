"""
Data Completeness Service
Deterministic field analysis without LLM
"""

from typing import Dict, List, Any


# Centralized field metadata map
FIELD_METADATA = {
    # Patient Demographics - CRITICAL for safety assessment
    "patient_age": {
        "category": "Patient Demographics",
        "criticality": "CRITICAL",
        "regulatory_reason": "Age affects drug metabolism, dosing calculations, and pediatric/geriatric risk assessment. Required for expedited reporting.",
        "weight": 10
    },
    "patient_sex": {
        "category": "Patient Demographics", 
        "criticality": "HIGH",
        "regulatory_reason": "Gender influences pharmacokinetics, hormone-drug interactions, and pregnancy-related contraindications.",
        "weight": 7
    },
    
    # Event Details - CRITICAL for causality
    "event_date": {
        "category": "Event Details",
        "criticality": "CRITICAL", 
        "regulatory_reason": "Temporal relationship between drug exposure and event onset is essential for causality assessment and regulatory timelines.",
        "weight": 10
    },
    "event_outcome": {
        "category": "Event Details",
        "criticality": "CRITICAL",
        "regulatory_reason": "Outcome determines seriousness classification (death, hospitalization, disability) and triggers mandatory expedited reporting.",
        "weight": 10
    },
    "adverse_event": {
        "category": "Event Details",
        "criticality": "CRITICAL",
        "regulatory_reason": "Core safety information required for signal detection and benefit-risk assessment.",
        "weight": 10
    },
    
    # Drug Information - CRITICAL for exposure assessment
    "suspect_drug": {
        "category": "Drug Information",
        "criticality": "CRITICAL",
        "regulatory_reason": "Primary drug under investigation. Mandatory for all adverse event reports.",
        "weight": 10
    },
    "drug_dose": {
        "category": "Drug Information",
        "criticality": "CRITICAL",
        "regulatory_reason": "Dose-response relationship critical for identifying overdose, underdose, or cumulative toxicity patterns.",
        "weight": 9
    },
    "drug_route": {
        "category": "Drug Information",
        "criticality": "HIGH",
        "regulatory_reason": "Route affects bioavailability, absorption rate, and local toxicity. IV vs oral can alter risk profile significantly.",
        "weight": 7
    },
    
    # Patient Identification - CRITICAL for CIOMS
    "patient_initials": {
        "category": "Patient Demographics",
        "criticality": "CRITICAL",
        "regulatory_reason": "Patient initials are required for CIOMS Form-I minimum case identification. Mandatory for all pharmacovigilance reports.",
        "weight": 10
    },
    
    # Reporter Information - HIGH priority (required CIOMS safety field)
    "reporter_type": {
        "category": "Reporter Information",
        "criticality": "HIGH",
        "regulatory_reason": "Report source identification is a required CIOMS safety field. Healthcare professional reports (MD, PharmD) carry higher medical certainty.",
        "weight": 8
    },
    "reporter_country": {
        "category": "Reporter Information",
        "criticality": "LOW",
        "regulatory_reason": "Geographic distribution helps identify regional safety signals, manufacturing issues, or genetic population differences.",
        "weight": 3
    },
    
    # Temporal Information
    "receipt_date": {
        "category": "Administrative",
        "criticality": "MEDIUM",
        "regulatory_reason": "Required for tracking regulatory reporting timelines (15-day vs 90-day reports).",
        "weight": 5
    }
}


class DataCompletenessService:
    """Deterministic data completeness analysis"""
    
    @staticmethod
    def analyze_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze case data completeness without LLM
        
        Returns:
            {
                "missing_fields": [...],
                "completeness_score": float,
                "critical_missing_count": int,
                "high_missing_count": int
            }
        """
        missing_fields = []
        critical_missing = 0
        high_missing = 0
        total_weight = 0
        obtained_weight = 0
        
        # Check each defined field
        for field_name, metadata in FIELD_METADATA.items():
            total_weight += metadata["weight"]
            
            # Check if field is missing or empty
            field_value = case_data.get(field_name)
            _PLACEHOLDER_VALUES = {
                "MISSING", "UNK", "N/A", "NA", "Unknown", "Not reported",
                "Not specified", "Not provided", "None", "NR", "NK",
                "not available", "unspecified", "n/a", "unknown",
            }
            is_missing = (
                field_value is None
                or field_value == ""
                or (isinstance(field_value, str) and field_value.strip() == "")
                or (isinstance(field_value, str) and field_value.strip() in _PLACEHOLDER_VALUES)
                or (field_name == "patient_age" and field_value == 0)
            )
            
            if is_missing:
                missing_fields.append({
                    "field": field_name,
                    "field_display": field_name.replace("_", " ").title(),
                    "category": metadata["category"],
                    "criticality": metadata["criticality"],
                    "safety_impact": metadata["regulatory_reason"]
                })
                
                if metadata["criticality"] == "CRITICAL":
                    critical_missing += 1
                elif metadata["criticality"] == "HIGH":
                    high_missing += 1
            else:
                # Field is present, add its weight
                obtained_weight += metadata["weight"]
        
        # Calculate completeness score (0.0 to 1.0)
        completeness_score = obtained_weight / total_weight if total_weight > 0 else 0.0
        
        return {
            "missing_fields": missing_fields,
            "completeness_score": round(completeness_score, 2),
            "critical_missing_count": critical_missing,
            "high_missing_count": high_missing,
            "total_fields_checked": len(FIELD_METADATA),
            "fields_present": len(FIELD_METADATA) - len(missing_fields)
        }

    @staticmethod
    def adjust_for_followup_status(
        base_score: float,
        followup_attempts: list = None,
    ) -> float:
        """
        Cap the reported completeness score based on follow-up status.

        Rationale: even if all *extracted* fields are present, the score
        should not read 100 % while follow-up is still outstanding —
        the reporter may have additional information we haven't collected.

        Caps:
            - No follow-ups sent yet           → max 0.85
            - Follow-up pending (no response)   → max 0.70
            - Follow-up sent, NO_RESPONSE       → max 0.60
            - All follow-ups responded           → base score (no cap)
        """
        if not followup_attempts:
            return min(base_score, 0.85)

        has_pending = any(
            getattr(a, "status", None) == "PENDING" for a in followup_attempts
        )
        has_no_response = any(
            getattr(a, "status", None) == "NO_RESPONSE" for a in followup_attempts
        )
        all_responded = all(
            getattr(a, "response_received", False) for a in followup_attempts
        )

        if all_responded:
            return base_score
        if has_no_response:
            return min(base_score, 0.60)
        if has_pending:
            return min(base_score, 0.70)
        return min(base_score, 0.85)
