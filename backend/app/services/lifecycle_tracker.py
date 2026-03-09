"""
Follow-Up Lifecycle Tracker Service
=====================================

Feature-4: Complete lifecycle tracking service.

This service manages:
- Lifecycle initialization
- Attempt tracking
- Reminder scheduling (24h compliance)
- Escalation logic
- Deadline awareness (7/15 day)
- Dead-case classification
- HCP vs Non-HCP policy application
- Audit logging

It does NOT:
- Score questions (Feature-3)
- Predict risk (Feature-1)
- Choose questions (Feature-3)

It only manages lifecycle state.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session
import logging
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# POLICY CONFIGURATION
# ============================================================================

@dataclass
class ReporterPolicyConfig:
    """Policy configuration for reporter type"""
    reporter_type: str  # HCP or NON_HCP
    max_attempts: int
    reminder_interval_hours: int
    questions_per_round: int
    escalation_after_attempts: int
    escalate_to: str
    allow_auto_dead_case: bool
    deadline_warning_days: int


# Default policies
HCP_POLICY = ReporterPolicyConfig(
    reporter_type="HCP",
    max_attempts=4,
    reminder_interval_hours=24,  # Compliance rule - cannot change
    questions_per_round=5,
    escalation_after_attempts=3,
    escalate_to="medical_team",
    allow_auto_dead_case=False,  # Must escalate first
    deadline_warning_days=2
)

NON_HCP_POLICY = ReporterPolicyConfig(
    reporter_type="NON_HCP",
    max_attempts=3,
    reminder_interval_hours=24,  # Compliance rule - cannot change
    questions_per_round=2,
    escalation_after_attempts=2,
    escalate_to="supervisor",
    allow_auto_dead_case=True,
    deadline_warning_days=2
)


def get_policy(reporter_type: str) -> ReporterPolicyConfig:
    """Get policy based on reporter type"""
    if reporter_type.upper() in ["MD", "HP", "PH", "HCP", "RPH", "RN"]:
        return HCP_POLICY
    return NON_HCP_POLICY


# ============================================================================
# LIFECYCLE TRACKER SERVICE
# ============================================================================

class FollowUpLifecycleTracker:
    """
    Main lifecycle tracking service.
    
    This is the operational spine of the follow-up system.
    """
    
    def __init__(self, db: Session = None):
        self.db = db
    
    # ========================================================================
    # STEP 1: INITIALIZE LIFECYCLE
    # ========================================================================
    
    def initialize_lifecycle(
        self,
        case_id: str,
        reporter_type: str,
        seriousness_level: str,
        case_created_at: datetime = None,
        initial_completeness: float = 0.0
    ) -> Dict[str, Any]:
        """
        Initialize lifecycle tracking for a new case.
        
        Called when Feature-1 determines follow-up is required.
        
        Args:
            case_id: Case UUID
            reporter_type: MD/HP/PT/CN etc
            seriousness_level: low/medium/high/critical
            case_created_at: When case was created
            initial_completeness: Starting completeness score
            
        Returns:
            Lifecycle tracking dict
        """
        case_created_at = case_created_at or datetime.utcnow()
        
        # Determine HCP vs Non-HCP
        hcp_types = ["MD", "HP", "PH", "HCP", "RPH", "RN"]
        is_hcp = reporter_type.upper() in hcp_types
        reporter_category = "HCP" if is_hcp else "NON_HCP"
        
        # Get policy
        policy = get_policy(reporter_type)
        
        # Calculate regulatory deadline
        if seriousness_level in ["high", "critical"]:
            deadline_days = 7
            deadline_type = "7_day"
        else:
            deadline_days = 15
            deadline_type = "15_day"
        
        regulatory_deadline = case_created_at + timedelta(days=deadline_days)
        days_remaining = (regulatory_deadline - datetime.utcnow()).days
        
        # Build lifecycle tracking
        lifecycle = {
            "lifecycle_id": str(uuid.uuid4()),
            "case_id": case_id,
            
            # Reporter segmentation
            "reporter_type": reporter_category,
            "reporter_subtype": reporter_type.upper(),
            
            # Attempt lifecycle
            "attempt_count": 0,
            "max_attempts": policy.max_attempts,
            "last_attempt_at": None,
            "next_reminder_due": None,
            "reminder_interval_hours": policy.reminder_interval_hours,
            
            # Response tracking
            "response_status": "pending",
            "last_response_at": None,
            "total_questions_sent": 0,
            "total_questions_answered": 0,
            
            # Question limits
            "questions_per_round": policy.questions_per_round,
            
            # Escalation
            "escalation_status": "none",
            "escalation_reason": None,
            "escalated_at": None,
            "escalated_to": None,
            
            # Regulatory deadlines
            "seriousness_level": seriousness_level,
            "regulatory_deadline": regulatory_deadline.isoformat(),
            "days_remaining": days_remaining,
            "deadline_type": deadline_type,
            
            # Completion metrics
            "completeness_score": initial_completeness,
            "safety_confidence_score": 0.0,
            "target_completeness": 0.85,
            "mandatory_fields_complete": False,
            
            # Closure
            "dead_case_flag": False,
            "closure_reason": None,
            "closed_at": None,
            
            # Status
            "lifecycle_status": "active",
            
            # Policy applied
            "policy_applied": f"{reporter_category}_POLICY",
            
            # Timestamps
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Log initialization
        audit_entry = self._create_audit_log(
            lifecycle_id=lifecycle["lifecycle_id"],
            case_id=case_id,
            action_type="CASE_CREATED",
            action_description=f"Lifecycle initialized for {reporter_category} reporter",
            reason=f"Seriousness: {seriousness_level}, Deadline: {deadline_type}",
            policy_applied=f"{reporter_category}_POLICY"
        )
        
        lifecycle["audit_log"] = [audit_entry]
        
        logger.info(f"✅ Lifecycle initialized for case {case_id}: {reporter_category}, {deadline_type}")
        
        return lifecycle
    
    # ========================================================================
    # STEP 2: RECORD FOLLOW-UP SENT
    # ========================================================================
    
    def record_followup_sent(
        self,
        lifecycle: Dict[str, Any],
        questions_sent: List[Dict],
        channel: str,
        sent_to: str = None
    ) -> Dict[str, Any]:
        """
        Record that a follow-up was sent.
        
        Updates attempt count and schedules next reminder.
        
        Args:
            lifecycle: Current lifecycle dict
            questions_sent: List of questions sent
            channel: EMAIL/WHATSAPP/PHONE/SMS
            sent_to: Recipient address
            
        Returns:
            Updated lifecycle dict
        """
        now = datetime.utcnow()
        
        # Update attempt count
        lifecycle["attempt_count"] += 1
        lifecycle["last_attempt_at"] = now.isoformat()
        lifecycle["total_questions_sent"] += len(questions_sent)
        
        # Schedule next reminder (24h compliance rule)
        reminder_hours = lifecycle.get("reminder_interval_hours", 24)
        lifecycle["next_reminder_due"] = (now + timedelta(hours=reminder_hours)).isoformat()
        
        # Update status
        lifecycle["lifecycle_status"] = "awaiting_response"
        lifecycle["response_status"] = "pending"
        
        # Update days remaining
        if lifecycle.get("regulatory_deadline"):
            deadline = datetime.fromisoformat(lifecycle["regulatory_deadline"])
            lifecycle["days_remaining"] = (deadline - now).days
        
        lifecycle["updated_at"] = now.isoformat()
        
        # Create attempt record
        attempt_record = {
            "attempt_id": str(uuid.uuid4()),
            "attempt_number": lifecycle["attempt_count"],
            "attempt_type": "initial" if lifecycle["attempt_count"] == 1 else "followup",
            "channel": channel,
            "sent_to": sent_to,
            "questions_sent": questions_sent,
            "questions_count": len(questions_sent),
            "sent_at": now.isoformat(),
            "response_received": False,
            "compliance_24h_met": True
        }
        
        if "attempts" not in lifecycle:
            lifecycle["attempts"] = []
        lifecycle["attempts"].append(attempt_record)
        
        # Audit log
        audit_entry = self._create_audit_log(
            lifecycle_id=lifecycle["lifecycle_id"],
            case_id=lifecycle["case_id"],
            action_type="FOLLOWUP_SENT",
            action_description=f"Follow-up #{lifecycle['attempt_count']} sent via {channel}",
            reason=f"Questions: {len(questions_sent)}"
        )
        lifecycle["audit_log"].append(audit_entry)
        
        logger.info(f"📤 Follow-up #{lifecycle['attempt_count']} sent for case {lifecycle['case_id']}")
        
        return lifecycle
    
    # ========================================================================
    # STEP 3: CHECK REMINDER DUE
    # ========================================================================
    
    def is_reminder_due(self, lifecycle: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if a reminder should be sent.
        
        Implements 24-hour compliance rule.
        
        Returns:
            (is_due, reason)
        """
        if lifecycle.get("response_status") == "complete":
            return False, "Case already complete"
        
        if lifecycle.get("dead_case_flag"):
            return False, "Case marked as dead"
        
        if lifecycle.get("lifecycle_status") in ["completed", "closed", "dead_case"]:
            return False, f"Case status is {lifecycle['lifecycle_status']}"
        
        next_reminder = lifecycle.get("next_reminder_due")
        if not next_reminder:
            return False, "No reminder scheduled"
        
        next_reminder_dt = datetime.fromisoformat(next_reminder)
        now = datetime.utcnow()
        
        if now >= next_reminder_dt:
            return True, "24-hour compliance reminder due"
        
        hours_remaining = (next_reminder_dt - now).total_seconds() / 3600
        return False, f"Reminder due in {hours_remaining:.1f} hours"
    
    # ========================================================================
    # STEP 4: SEND REMINDER
    # ========================================================================
    
    def record_reminder_sent(
        self,
        lifecycle: Dict[str, Any],
        channel: str
    ) -> Dict[str, Any]:
        """
        Record that a reminder was sent.
        
        24-hour compliance reminder.
        """
        now = datetime.utcnow()
        
        # Update attempt count
        lifecycle["attempt_count"] += 1
        lifecycle["last_attempt_at"] = now.isoformat()
        
        # Schedule next reminder
        reminder_hours = lifecycle.get("reminder_interval_hours", 24)
        lifecycle["next_reminder_due"] = (now + timedelta(hours=reminder_hours)).isoformat()
        
        # Update days remaining
        if lifecycle.get("regulatory_deadline"):
            deadline = datetime.fromisoformat(lifecycle["regulatory_deadline"])
            lifecycle["days_remaining"] = (deadline - now).days
        
        lifecycle["updated_at"] = now.isoformat()
        
        # Update last attempt in attempts list
        if lifecycle.get("attempts"):
            last_attempt = lifecycle["attempts"][-1]
            last_attempt["reminder_sent"] = True
            last_attempt["reminder_sent_at"] = now.isoformat()
        
        # Audit log
        audit_entry = self._create_audit_log(
            lifecycle_id=lifecycle["lifecycle_id"],
            case_id=lifecycle["case_id"],
            action_type="REMINDER_SENT",
            action_description=f"24-hour compliance reminder #{lifecycle['attempt_count']} sent",
            reason="24-hour compliance rule"
        )
        lifecycle["audit_log"].append(audit_entry)
        
        logger.info(f"⏰ Reminder #{lifecycle['attempt_count']} sent for case {lifecycle['case_id']}")
        
        return lifecycle
    
    # ========================================================================
    # STEP 5: RECORD RESPONSE RECEIVED
    # ========================================================================
    
    def record_response_received(
        self,
        lifecycle: Dict[str, Any],
        questions_answered: int,
        completeness_score: float,
        safety_confidence: float,
        is_complete: bool = False
    ) -> Dict[str, Any]:
        """
        Record that a response was received from reporter.
        
        Updates completion metrics and determines next action.
        """
        now = datetime.utcnow()
        
        # Update response tracking
        lifecycle["last_response_at"] = now.isoformat()
        lifecycle["total_questions_answered"] += questions_answered
        lifecycle["completeness_score"] = completeness_score
        lifecycle["safety_confidence_score"] = safety_confidence
        
        # Determine response status
        if is_complete or completeness_score >= lifecycle.get("target_completeness", 0.85):
            lifecycle["response_status"] = "complete"
            lifecycle["lifecycle_status"] = "completed"
            lifecycle["mandatory_fields_complete"] = True
        elif questions_answered > 0:
            lifecycle["response_status"] = "partial"
            lifecycle["lifecycle_status"] = "active"
        else:
            lifecycle["response_status"] = "pending"
        
        lifecycle["updated_at"] = now.isoformat()
        
        # Update last attempt
        if lifecycle.get("attempts"):
            last_attempt = lifecycle["attempts"][-1]
            last_attempt["response_received"] = True
            last_attempt["response_received_at"] = now.isoformat()
            last_attempt["questions_answered"] = questions_answered
            last_attempt["response_type"] = "full" if is_complete else "partial"
        
        # Audit log
        audit_entry = self._create_audit_log(
            lifecycle_id=lifecycle["lifecycle_id"],
            case_id=lifecycle["case_id"],
            action_type="RESPONSE_RECEIVED",
            action_description=f"Response received: {questions_answered} questions answered",
            reason=f"Completeness: {completeness_score:.0%}, Status: {lifecycle['response_status']}"
        )
        lifecycle["audit_log"].append(audit_entry)
        
        logger.info(f"📥 Response received for case {lifecycle['case_id']}: {lifecycle['response_status']}")
        
        return lifecycle
    
    # ========================================================================
    # STEP 6: CHECK ESCALATION NEEDED
    # ========================================================================
    
    def check_escalation_needed(
        self,
        lifecycle: Dict[str, Any]
    ) -> Tuple[bool, str, str]:
        """
        Check if escalation is needed.
        
        Escalation triggers:
        1. Max attempts reached
        2. Days remaining < 2
        3. High seriousness + no response
        
        Returns:
            (needs_escalation, reason, escalate_to)
        """
        policy = get_policy(lifecycle.get("reporter_subtype", "NON_HCP"))
        
        attempt_count = lifecycle.get("attempt_count", 0)
        days_remaining = lifecycle.get("days_remaining", 15)
        seriousness = lifecycle.get("seriousness_level", "medium")
        response_status = lifecycle.get("response_status", "pending")
        
        # Already escalated?
        if lifecycle.get("escalation_status") in ["escalated_to_reviewer", "escalated_to_medical"]:
            return False, "Already escalated", None
        
        # Condition 1: Max attempts reached (but not exceeded max)
        if attempt_count >= policy.escalation_after_attempts:
            return True, f"Reached {attempt_count} attempts (threshold: {policy.escalation_after_attempts})", policy.escalate_to
        
        # Condition 2: Deadline approaching
        if days_remaining <= policy.deadline_warning_days:
            return True, f"Only {days_remaining} days remaining until deadline", policy.escalate_to
        
        # Condition 3: High seriousness + no response after 2 attempts
        if seriousness in ["high", "critical"] and response_status == "pending" and attempt_count >= 2:
            return True, f"High seriousness case with no response after {attempt_count} attempts", "medical_team"
        
        return False, "No escalation needed", None
    
    # ========================================================================
    # STEP 7: TRIGGER ESCALATION
    # ========================================================================
    
    def trigger_escalation(
        self,
        lifecycle: Dict[str, Any],
        reason: str,
        escalate_to: str
    ) -> Dict[str, Any]:
        """
        Trigger escalation for a case.
        """
        now = datetime.utcnow()
        
        # Determine escalation status based on target
        if escalate_to == "medical_team":
            escalation_status = "escalated_to_medical"
        else:
            escalation_status = "escalated_to_reviewer"
        
        lifecycle["escalation_status"] = escalation_status
        lifecycle["escalation_reason"] = reason
        lifecycle["escalated_at"] = now.isoformat()
        lifecycle["escalated_to"] = escalate_to
        lifecycle["lifecycle_status"] = "escalated"
        lifecycle["updated_at"] = now.isoformat()
        
        # Audit log
        audit_entry = self._create_audit_log(
            lifecycle_id=lifecycle["lifecycle_id"],
            case_id=lifecycle["case_id"],
            action_type="ESCALATION_TRIGGERED",
            action_description=f"Case escalated to {escalate_to}",
            reason=reason
        )
        lifecycle["audit_log"].append(audit_entry)
        
        logger.warning(f"🚨 Case {lifecycle['case_id']} ESCALATED to {escalate_to}: {reason}")
        
        return lifecycle
    
    # ========================================================================
    # STEP 8: CHECK DEAD CASE
    # ========================================================================
    
    def check_dead_case(
        self,
        lifecycle: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Check if case should be marked as dead.
        
        Dead case conditions:
        1. Max attempts exceeded + no response
        2. Completeness still below threshold
        
        Policy-controlled - HCP cases must escalate first.
        
        Returns:
            (is_dead, reason)
        """
        policy = get_policy(lifecycle.get("reporter_subtype", "NON_HCP"))
        
        # HCP cases cannot auto-close
        if not policy.allow_auto_dead_case:
            if lifecycle.get("escalation_status") not in ["escalated_to_reviewer", "escalated_to_medical"]:
                return False, "HCP policy requires escalation before dead case"
        
        attempt_count = lifecycle.get("attempt_count", 0)
        max_attempts = lifecycle.get("max_attempts", policy.max_attempts)
        response_status = lifecycle.get("response_status", "pending")
        completeness = lifecycle.get("completeness_score", 0.0)
        target = lifecycle.get("target_completeness", 0.85)
        
        # Already complete?
        if response_status == "complete" or completeness >= target:
            return False, "Case is complete"
        
        # Max attempts exceeded + no meaningful response
        if attempt_count >= max_attempts and response_status in ["pending", "no_response"]:
            return True, f"No response after {attempt_count} attempts (max: {max_attempts})"
        
        return False, "Case still active"
    
    # ========================================================================
    # STEP 9: MARK DEAD CASE
    # ========================================================================
    
    def mark_dead_case(
        self,
        lifecycle: Dict[str, Any],
        reason: str,
        closed_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Mark case as dead.
        
        This is POLICY-CONTROLLED - AI cannot override.
        """
        now = datetime.utcnow()
        
        lifecycle["dead_case_flag"] = True
        lifecycle["closure_reason"] = reason
        lifecycle["closed_at"] = now.isoformat()
        lifecycle["closed_by"] = closed_by
        lifecycle["lifecycle_status"] = "dead_case"
        lifecycle["response_status"] = "no_response"
        lifecycle["updated_at"] = now.isoformat()
        
        # Audit log
        audit_entry = self._create_audit_log(
            lifecycle_id=lifecycle["lifecycle_id"],
            case_id=lifecycle["case_id"],
            action_type="DEAD_CASE_MARKED",
            action_description="Case marked as dead",
            reason=reason,
            actor=closed_by
        )
        lifecycle["audit_log"].append(audit_entry)
        
        logger.warning(f"☠️ Case {lifecycle['case_id']} marked as DEAD: {reason}")
        
        return lifecycle
    
    # ========================================================================
    # STEP 10: CLOSE CASE (Success)
    # ========================================================================
    
    def close_case_success(
        self,
        lifecycle: Dict[str, Any],
        closed_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Close case successfully (completeness achieved).
        """
        now = datetime.utcnow()
        
        lifecycle["lifecycle_status"] = "closed"
        lifecycle["response_status"] = "complete"
        lifecycle["closure_reason"] = "Target completeness achieved"
        lifecycle["closed_at"] = now.isoformat()
        lifecycle["closed_by"] = closed_by
        lifecycle["updated_at"] = now.isoformat()
        
        # Audit log
        audit_entry = self._create_audit_log(
            lifecycle_id=lifecycle["lifecycle_id"],
            case_id=lifecycle["case_id"],
            action_type="CASE_CLOSED",
            action_description="Case closed successfully",
            reason=f"Completeness: {lifecycle['completeness_score']:.0%}",
            actor=closed_by
        )
        lifecycle["audit_log"].append(audit_entry)
        
        logger.info(f"✅ Case {lifecycle['case_id']} CLOSED successfully")
        
        return lifecycle
    
    # ========================================================================
    # STEP 11: UPDATE DAYS REMAINING
    # ========================================================================
    
    def update_deadline_awareness(
        self,
        lifecycle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update deadline awareness.
        
        Called periodically to check deadline status.
        """
        if not lifecycle.get("regulatory_deadline"):
            return lifecycle
        
        deadline = datetime.fromisoformat(lifecycle["regulatory_deadline"])
        now = datetime.utcnow()
        days_remaining = (deadline - now).days
        
        lifecycle["days_remaining"] = days_remaining
        
        # Check for deadline warning
        policy = get_policy(lifecycle.get("reporter_subtype", "NON_HCP"))
        
        if days_remaining <= 0:
            # Deadline passed - force escalation
            if lifecycle.get("escalation_status") not in ["escalated_to_reviewer", "escalated_to_medical"]:
                lifecycle = self.trigger_escalation(
                    lifecycle,
                    reason="Regulatory deadline passed!",
                    escalate_to="medical_team"
                )
                
                # Additional audit entry
                audit_entry = self._create_audit_log(
                    lifecycle_id=lifecycle["lifecycle_id"],
                    case_id=lifecycle["case_id"],
                    action_type="DEADLINE_PASSED",
                    action_description="Regulatory deadline has passed",
                    reason=f"Deadline was: {lifecycle['regulatory_deadline']}"
                )
                lifecycle["audit_log"].append(audit_entry)
        
        elif days_remaining <= policy.deadline_warning_days:
            # Deadline approaching
            if lifecycle.get("escalation_status") == "none":
                lifecycle["escalation_status"] = "urgent"
                
                audit_entry = self._create_audit_log(
                    lifecycle_id=lifecycle["lifecycle_id"],
                    case_id=lifecycle["case_id"],
                    action_type="DEADLINE_WARNING",
                    action_description=f"Only {days_remaining} days until deadline",
                    reason="Deadline approaching"
                )
                lifecycle["audit_log"].append(audit_entry)
        
        lifecycle["updated_at"] = datetime.utcnow().isoformat()
        
        return lifecycle
    
    # ========================================================================
    # HELPER: CREATE AUDIT LOG ENTRY
    # ========================================================================
    
    def _create_audit_log(
        self,
        lifecycle_id: str,
        case_id: str,
        action_type: str,
        action_description: str,
        reason: str = None,
        actor: str = "system",
        policy_applied: str = None
    ) -> Dict[str, Any]:
        """Create an audit log entry"""
        return {
            "log_id": str(uuid.uuid4()),
            "lifecycle_id": lifecycle_id,
            "case_id": case_id,
            "action_type": action_type,
            "action_description": action_description,
            "reason": reason,
            "actor": actor,
            "actor_type": "system" if actor == "system" else "human",
            "policy_applied": policy_applied,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # GET LIFECYCLE SUMMARY
    # ========================================================================
    
    def get_lifecycle_summary(self, lifecycle: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of lifecycle status"""
        return {
            "case_id": lifecycle.get("case_id"),
            "reporter_type": lifecycle.get("reporter_type"),
            "lifecycle_status": lifecycle.get("lifecycle_status"),
            "attempt_count": lifecycle.get("attempt_count"),
            "max_attempts": lifecycle.get("max_attempts"),
            "response_status": lifecycle.get("response_status"),
            "escalation_status": lifecycle.get("escalation_status"),
            "days_remaining": lifecycle.get("days_remaining"),
            "completeness_score": lifecycle.get("completeness_score"),
            "dead_case_flag": lifecycle.get("dead_case_flag"),
            "policy_applied": lifecycle.get("policy_applied"),
            "next_action": self._determine_next_action(lifecycle)
        }
    
    def _determine_next_action(self, lifecycle: Dict[str, Any]) -> str:
        """Determine the next action needed"""
        status = lifecycle.get("lifecycle_status")
        
        if status == "completed":
            return "NONE - Case complete"
        elif status == "dead_case":
            return "NONE - Case dead"
        elif status == "closed":
            return "NONE - Case closed"
        elif status == "escalated":
            return "AWAIT_HUMAN_REVIEW"
        
        # Check reminder
        is_due, reason = self.is_reminder_due(lifecycle)
        if is_due:
            return "SEND_REMINDER"
        
        # Check escalation
        needs_esc, esc_reason, _ = self.check_escalation_needed(lifecycle)
        if needs_esc:
            return "ESCALATE"
        
        # Check dead case
        is_dead, dead_reason = self.check_dead_case(lifecycle)
        if is_dead:
            return "MARK_DEAD"
        
        if lifecycle.get("response_status") == "pending":
            return "AWAIT_RESPONSE"
        elif lifecycle.get("response_status") == "partial":
            return "SEND_FOLLOWUP"
        
        return "CONTINUE_MONITORING"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_lifecycle_tracker(db: Session = None) -> FollowUpLifecycleTracker:
    """Create a lifecycle tracker instance"""
    return FollowUpLifecycleTracker(db)


# ============================================================================
# TEST
# ============================================================================

def test_lifecycle_tracker():
    """Test the lifecycle tracker"""
    print("=" * 70)
    print("TESTING FOLLOW-UP LIFECYCLE TRACKER")
    print("=" * 70)
    
    tracker = FollowUpLifecycleTracker()
    
    # Test Case 1: HCP reporter, high seriousness
    print("\n📋 Test 1: HCP Reporter, High Seriousness")
    print("-" * 50)
    
    lifecycle = tracker.initialize_lifecycle(
        case_id="test-case-001",
        reporter_type="MD",
        seriousness_level="high",
        initial_completeness=0.3
    )
    
    print(f"Reporter Type: {lifecycle['reporter_type']}")
    print(f"Max Attempts: {lifecycle['max_attempts']}")
    print(f"Questions/Round: {lifecycle['questions_per_round']}")
    print(f"Deadline Type: {lifecycle['deadline_type']}")
    print(f"Days Remaining: {lifecycle['days_remaining']}")
    
    # Send first follow-up
    lifecycle = tracker.record_followup_sent(
        lifecycle,
        questions_sent=[{"q": "What was the dose?"}],
        channel="EMAIL"
    )
    print(f"\n📤 After first follow-up:")
    print(f"Attempt Count: {lifecycle['attempt_count']}")
    print(f"Status: {lifecycle['lifecycle_status']}")
    
    # Test Case 2: Non-HCP reporter
    print("\n\n📋 Test 2: Non-HCP Reporter, Medium Seriousness")
    print("-" * 50)
    
    lifecycle2 = tracker.initialize_lifecycle(
        case_id="test-case-002",
        reporter_type="CN",
        seriousness_level="medium",
        initial_completeness=0.4
    )
    
    print(f"Reporter Type: {lifecycle2['reporter_type']}")
    print(f"Max Attempts: {lifecycle2['max_attempts']}")
    print(f"Questions/Round: {lifecycle2['questions_per_round']}")
    print(f"Deadline Type: {lifecycle2['deadline_type']}")
    
    # Simulate multiple attempts with no response
    for i in range(3):
        lifecycle2 = tracker.record_followup_sent(
            lifecycle2,
            questions_sent=[{"q": f"Question {i+1}"}],
            channel="WHATSAPP"
        )
    
    print(f"\n📤 After 3 follow-ups:")
    print(f"Attempt Count: {lifecycle2['attempt_count']}")
    
    # Check dead case
    is_dead, reason = tracker.check_dead_case(lifecycle2)
    print(f"Is Dead Case: {is_dead}")
    print(f"Reason: {reason}")
    
    if is_dead:
        lifecycle2 = tracker.mark_dead_case(lifecycle2, reason)
        print(f"Status: {lifecycle2['lifecycle_status']}")
    
    # Print summary
    print("\n\n📊 Lifecycle Summaries:")
    print("-" * 50)
    
    summary1 = tracker.get_lifecycle_summary(lifecycle)
    print(f"\nCase 1 (HCP):")
    for k, v in summary1.items():
        print(f"  {k}: {v}")
    
    summary2 = tracker.get_lifecycle_summary(lifecycle2)
    print(f"\nCase 2 (Non-HCP):")
    for k, v in summary2.items():
        print(f"  {k}: {v}")
    
    # Print audit log
    print("\n\n📜 Audit Log (Case 2):")
    print("-" * 50)
    for entry in lifecycle2.get("audit_log", [])[-5:]:
        print(f"  [{entry['timestamp'][:19]}] {entry['action_type']}: {entry['action_description']}")


if __name__ == "__main__":
    test_lifecycle_tracker()
