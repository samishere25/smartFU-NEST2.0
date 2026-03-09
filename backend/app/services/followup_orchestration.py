"""
Follow-Up Orchestration Service (Feature 4)
Deterministic rule-based follow-up decision-making and channel selection.
NO AI/LLM - pure business logic based on Feature 3 question scoring.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class FollowUpOrchestrator:
    """
    Deterministic follow-up orchestration based on Feature 3 question scoring.
    
    Decision Rules:
    1. If CRITICAL questions exist → follow-up REQUIRED
    2. If only MEDIUM questions → follow-up OPTIONAL  
    3. If completeness >= threshold → NO follow-up
    4. If stop_followup = True → NO follow-up
    
    Channel Selection (reporter type based):
    - HP (Health Professional) → EMAIL
    - MD (Medical Doctor) → EMAIL
    - PT (Patient) + CRITICAL → PHONE
    - PT + non-critical → EMAIL
    - CN (Consumer) → EMAIL
    - Unknown → EMAIL (default)
    
    Timing Rules:
    - CRITICAL → immediate (0 hours)
    - HIGH → within 48 hours
    - MEDIUM → defer (168 hours = 7 days)
    - LOW → skip (no follow-up)
    """
    
    # Reporter type mappings (from FAERS data)
    REPORTER_TYPES = {
        'HP': 'Health Professional',
        'MD': 'Medical Doctor',
        'PT': 'Patient',
        'CN': 'Consumer',
        'LW': 'Lawyer',
        'OT': 'Other'
    }
    
    # Channel priorities by reporter type
    CHANNEL_RULES = {
        'HP': 'EMAIL',      # Health professionals prefer email
        'MD': 'EMAIL',      # Doctors prefer email
        'PT': 'PHONE',      # Patients - depends on criticality (see below)
        'CN': 'EMAIL',      # Consumers prefer email
        'LW': 'EMAIL',      # Lawyers prefer formal email
        'OT': 'EMAIL'       # Default to email
    }
    
    # Timing by criticality (hours)
    TIMING_RULES = {
        'CRITICAL': 0,      # Immediate
        'HIGH': 48,         # 2 days
        'MEDIUM': 168,      # 7 days  
        'LOW': None         # Never follow up
    }
    
    # Completeness threshold to skip follow-up
    COMPLETENESS_THRESHOLD = 0.85
    
    @staticmethod
    def should_create_followup(
        questions: List[Dict],
        stop_followup: bool,
        completeness_score: float,
        decision: str
    ) -> Tuple[bool, str]:
        """
        Determine if follow-up should be created.
        
        Args:
            questions: List of selected questions from Feature 3
            stop_followup: Adaptive stopping flag from Feature 3
            completeness_score: Data completeness (0.0-1.0)
            decision: Case decision (SKIP, MONITOR, etc.)
        
        Returns:
            (should_create, reason)
        """
        # Rule 1: Adaptive stopping already decided - no follow-up
        if stop_followup:
            return False, "Adaptive stopping triggered - no follow-up needed"
        
        # Rule 2: No questions selected - no follow-up
        if not questions or len(questions) == 0:
            return False, "No questions selected - sufficient data"
        
        # Rule 3: High completeness - no follow-up
        if completeness_score >= FollowUpOrchestrator.COMPLETENESS_THRESHOLD:
            return False, f"High completeness ({completeness_score:.0%}) - no follow-up needed"
        
        # Rule 4: Decision is SKIP - no follow-up
        if decision == "SKIP":
            return False, "Decision is SKIP - no action required"
        
        # Rule 5: Has questions and not stopped - create follow-up
        critical_count = sum(1 for q in questions if q.get('criticality') == 'CRITICAL')
        high_count = sum(1 for q in questions if q.get('criticality') == 'HIGH')
        
        if critical_count > 0:
            return True, f"CRITICAL questions detected ({critical_count} questions)"
        elif high_count > 0:
            return True, f"HIGH priority questions detected ({high_count} questions)"
        else:
            return True, f"Follow-up questions selected ({len(questions)} questions)"
    
    @staticmethod
    def select_channel(
        reporter_type: str,
        questions: List[Dict]
    ) -> str:
        """
        Select optimal communication channel based on reporter type and question criticality.
        
        Args:
            reporter_type: Reporter type code (HP, MD, PT, CN, etc.)
            questions: List of questions to ask
        
        Returns:
            Channel name: EMAIL or PHONE
        """
        # Normalize reporter type
        reporter_type = (reporter_type or 'OT').upper().strip()
        
        # Check if any CRITICAL questions exist
        has_critical = any(q.get('criticality') == 'CRITICAL' for q in questions)
        
        # Special rule for patients with critical questions
        if reporter_type == 'PT' and has_critical:
            return 'PHONE'  # Call patients for critical safety issues
        
        # Otherwise use default channel for reporter type
        return FollowUpOrchestrator.CHANNEL_RULES.get(reporter_type, 'EMAIL')
    
    @staticmethod
    def calculate_timing(
        questions: List[Dict]
    ) -> int:
        """
        Calculate optimal follow-up timing in hours based on question criticality.
        
        Uses the MOST critical question to determine timing (conservative approach).
        
        Args:
            questions: List of questions
        
        Returns:
            Hours until follow-up should be sent
        """
        if not questions:
            return 0
        
        # Find most critical question
        criticality_priority = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        most_critical = min(
            questions,
            key=lambda q: criticality_priority.get(q.get('criticality', 'LOW'), 999)
        )
        
        criticality = most_critical.get('criticality', 'MEDIUM')
        return FollowUpOrchestrator.TIMING_RULES.get(criticality, 168)
    
    @staticmethod
    def orchestrate_followup(
        case_id: str,
        questions: List[Dict],
        stop_followup: bool,
        completeness_score: float,
        risk_score: float,
        decision: str,
        reporter_type: str,
        primaryid: int
    ) -> Dict:
        """
        Main orchestration function - creates follow-up decision.
        
        Args:
            case_id: UUID of case
            questions: Selected questions from Feature 3
            stop_followup: Adaptive stopping flag
            completeness_score: Data completeness (0.0-1.0)
            risk_score: Risk score (0.0-1.0)
            decision: Case decision
            reporter_type: Reporter type code
            primaryid: FAERS primary ID
        
        Returns:
            Follow-up orchestration result dict
        """
        # Determine if follow-up should be created
        should_create, reason = FollowUpOrchestrator.should_create_followup(
            questions=questions,
            stop_followup=stop_followup,
            completeness_score=completeness_score,
            decision=decision
        )
        
        # If no follow-up needed, return early
        if not should_create:
            return {
                "followup_required": False,
                "followup_created": False,
                "reason": reason,
                "questions_count": 0,
                "channel": None,
                "timing_hours": None,
                "status": "NOT_REQUIRED"
            }
        
        # Select channel
        channel = FollowUpOrchestrator.select_channel(
            reporter_type=reporter_type,
            questions=questions
        )
        
        # Calculate timing
        timing_hours = FollowUpOrchestrator.calculate_timing(questions)
        
        # Count question types
        critical_count = sum(1 for q in questions if q.get('criticality') == 'CRITICAL')
        high_count = sum(1 for q in questions if q.get('criticality') == 'HIGH')
        medium_count = sum(1 for q in questions if q.get('criticality') == 'MEDIUM')
        
        # Determine priority
        if critical_count > 0:
            priority = "CRITICAL"
        elif high_count > 0:
            priority = "HIGH"
        else:
            priority = "MEDIUM"
        
        # Build response
        return {
            "followup_required": True,
            "followup_created": True,
            "reason": reason,
            "questions_count": len(questions),
            "questions": questions,  # Full question list for storage
            "channel": channel,
            "timing_hours": timing_hours,
            "scheduled_at": datetime.utcnow() + timedelta(hours=timing_hours),
            "priority": priority,
            "status": "PENDING",
            "reporter_type": reporter_type,
            "reporter_type_display": FollowUpOrchestrator.REPORTER_TYPES.get(
                reporter_type, 'Unknown'
            ),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "metadata": {
                "case_id": case_id,
                "primaryid": primaryid,
                "completeness_score": completeness_score,
                "risk_score": risk_score,
                "decision": decision,
                "orchestrated_at": datetime.utcnow().isoformat()
            }
        }
    
    @staticmethod
    def create_followup_message(
        questions: List[Dict],
        channel: str,
        reporter_type: str
    ) -> str:
        """
        Generate follow-up message template (NOT sent, just prepared).
        
        Args:
            questions: List of questions
            channel: Communication channel
            reporter_type: Reporter type
        
        Returns:
            Message template string
        """
        greeting = "Dear Healthcare Professional" if reporter_type in ['HP', 'MD'] else "Dear Reporter"
        
        question_list = "\n".join([
            f"{i+1}. {q.get('question', q.get('field_name', 'Question'))}"
            for i, q in enumerate(questions)
        ])
        
        urgency_note = ""
        if any(q.get('criticality') == 'CRITICAL' for q in questions):
            urgency_note = "\n\n⚠️ URGENT: This case contains critical safety information gaps. Please respond as soon as possible."
        
        return f"""
{greeting},

We are following up on the adverse event report (Case {questions[0].get('field_name', 'N/A')}) to collect additional safety information.

Please provide the following information:

{question_list}
{urgency_note}

Thank you for your cooperation in improving drug safety.

SmartFU Pharmacovigilance System
(This is a simulated follow-up - no actual communication sent)
        """.strip()
