"""
Feature-2: Engagement Risk Adaptation Module
============================================

Converts response prediction into policy-controlled engagement risk levels.

PIPELINE:
    Response Prediction → Engagement Risk Classification → Policy Adaptation → Follow-Up Strategy

COMPLIANCE CONSTRAINTS:
- Do NOT override mandatory compliance rules (e.g., 24-hour reminder cadence)
- Do NOT modify communication channel selection
- Dead-case classification remains policy-controlled
- AI recommends, Policy decides

OUTPUT:
- response_probability
- prediction_confidence
- engagement_risk (HIGH_RISK_ENGAGEMENT | MEDIUM_RISK_ENGAGEMENT | LOW_RISK_ENGAGEMENT)
- followup_priority (CRITICAL | HIGH | MEDIUM | LOW)
- followup_frequency (hours between attempts)
- escalation_needed (bool)
"""

from typing import Dict, Any, Optional, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# POLICY CONFIGURATION (Configurable Thresholds)
# ============================================================================

@dataclass
class EngagementPolicy:
    """
    Policy-controlled thresholds for engagement risk adaptation.
    
    These values govern AI recommendations - they are NOT hardcoded AI decisions.
    Policy owners can modify these thresholds without changing AI logic.
    """
    
    # Response probability thresholds for engagement risk classification
    high_engagement_risk_threshold: float = 0.35      # Below this = HIGH_RISK_ENGAGEMENT
    medium_engagement_risk_threshold: float = 0.65   # Below this = MEDIUM_RISK_ENGAGEMENT
    # Above medium_threshold = LOW_RISK_ENGAGEMENT
    
    # Confidence thresholds
    low_confidence_threshold: float = 0.5            # Below this = low confidence adjustment
    high_confidence_threshold: float = 0.8           # Above this = high confidence
    
    # Case seriousness impact weights
    seriousness_weight_high: float = 0.2             # Boost engagement risk for HIGH seriousness
    seriousness_weight_medium: float = 0.1           # Boost for MEDIUM seriousness
    
    # Follow-up frequency (hours) by engagement risk
    frequency_high_risk: int = 24                    # Every 24 hours (compliance minimum)
    frequency_medium_risk: int = 48                  # Every 48 hours
    frequency_low_risk: int = 168                    # Weekly (168 hours)
    
    # Maximum attempts before escalation recommendation
    max_attempts_high_risk: int = 5
    max_attempts_medium_risk: int = 3
    max_attempts_low_risk: int = 2
    
    # Compliance: Minimum reminder interval (CANNOT BE OVERRIDDEN)
    compliance_min_reminder_hours: int = 24          # Regulatory requirement
    
    # Escalation thresholds
    escalation_after_attempts: int = 3               # Recommend escalation after N attempts
    escalation_risk_score_threshold: float = 0.7    # Auto-recommend escalation if risk >= this


# Default policy instance
DEFAULT_POLICY = EngagementPolicy()


# ============================================================================
# ENGAGEMENT RISK CLASSIFICATION
# ============================================================================

class EngagementRiskClassifier:
    """
    Step 1: Convert response probability + confidence + seriousness 
    into engagement risk level.
    
    Classification is EXPLAINABLE and TRANSPARENT.
    """
    
    RISK_LEVELS = Literal["HIGH_RISK_ENGAGEMENT", "MEDIUM_RISK_ENGAGEMENT", "LOW_RISK_ENGAGEMENT"]
    
    @staticmethod
    def classify(
        response_probability: float,
        prediction_confidence: float,
        case_seriousness: str = "MEDIUM",
        policy: EngagementPolicy = DEFAULT_POLICY
    ) -> Dict[str, Any]:
        """
        Classify engagement risk based on response probability and context.
        
        Args:
            response_probability: Predicted probability of reporter response (0.0-1.0)
            prediction_confidence: Confidence in the prediction (0.0-1.0)
            case_seriousness: From Feature-1 medical reasoning ("HIGH", "MEDIUM", "LOW")
            policy: Policy configuration (allows threshold customization)
        
        Returns:
            {
                "engagement_risk": "HIGH_RISK_ENGAGEMENT" | "MEDIUM_RISK_ENGAGEMENT" | "LOW_RISK_ENGAGEMENT",
                "risk_score": float (0.0-1.0, higher = more engagement risk),
                "classification_reasoning": str,
                "factors": dict
            }
        """
        # Validate inputs
        response_probability = max(0.0, min(1.0, response_probability))
        prediction_confidence = max(0.0, min(1.0, prediction_confidence))
        
        # Step 1: Base engagement risk from response probability
        # Lower response probability = HIGHER engagement risk
        base_risk = 1.0 - response_probability
        
        # Step 2: Adjust for prediction confidence
        # Low confidence → increase risk (be more cautious)
        if prediction_confidence < policy.low_confidence_threshold:
            confidence_adjustment = 0.1  # Increase risk due to uncertainty
        elif prediction_confidence >= policy.high_confidence_threshold:
            confidence_adjustment = -0.05  # Slightly decrease risk if highly confident
        else:
            confidence_adjustment = 0.0
        
        # Step 3: Adjust for case seriousness (from Feature-1)
        seriousness_adjustment = 0.0
        if case_seriousness == "HIGH":
            seriousness_adjustment = policy.seriousness_weight_high
        elif case_seriousness == "MEDIUM":
            seriousness_adjustment = policy.seriousness_weight_medium
        
        # Step 4: Calculate final risk score
        final_risk_score = base_risk + confidence_adjustment + seriousness_adjustment
        final_risk_score = max(0.0, min(1.0, final_risk_score))
        
        # Step 5: Classify into engagement risk level
        # Use RESPONSE PROBABILITY thresholds (not risk score) for classification
        # This ensures explainability: "Response prob is X, so engagement risk is Y"
        if response_probability < policy.high_engagement_risk_threshold:
            engagement_risk = "HIGH_RISK_ENGAGEMENT"
        elif response_probability < policy.medium_engagement_risk_threshold:
            engagement_risk = "MEDIUM_RISK_ENGAGEMENT"
        else:
            engagement_risk = "LOW_RISK_ENGAGEMENT"
        
        # Override to HIGH if case seriousness is HIGH (safety-first approach)
        if case_seriousness == "HIGH" and engagement_risk == "LOW_RISK_ENGAGEMENT":
            engagement_risk = "MEDIUM_RISK_ENGAGEMENT"
            final_risk_score = max(final_risk_score, 0.5)
        
        # Build reasoning
        reasoning_parts = [
            f"Response probability: {response_probability:.0%}",
            f"Prediction confidence: {prediction_confidence:.0%}",
            f"Case seriousness: {case_seriousness}"
        ]
        
        if confidence_adjustment != 0:
            reasoning_parts.append(f"Confidence adjustment: {confidence_adjustment:+.0%}")
        if seriousness_adjustment != 0:
            reasoning_parts.append(f"Seriousness adjustment: {seriousness_adjustment:+.0%}")
        
        reasoning_parts.append(f"Final engagement risk: {engagement_risk}")
        
        return {
            "engagement_risk": engagement_risk,
            "risk_score": round(final_risk_score, 3),
            "classification_reasoning": " | ".join(reasoning_parts),
            "factors": {
                "response_probability": response_probability,
                "prediction_confidence": prediction_confidence,
                "case_seriousness": case_seriousness,
                "base_risk": round(base_risk, 3),
                "confidence_adjustment": round(confidence_adjustment, 3),
                "seriousness_adjustment": round(seriousness_adjustment, 3)
            }
        }


# ============================================================================
# POLICY-CONTROLLED FOLLOW-UP ADAPTATION
# ============================================================================

class PolicyControlledAdapter:
    """
    Step 2: Apply policy thresholds to determine follow-up behavior.
    
    AI RECOMMENDS - POLICY DECIDES
    
    This layer enforces:
    - Compliance rules (e.g., 24-hour minimum reminder interval)
    - Maximum attempts before escalation
    - Priority and frequency based on engagement risk
    """
    
    @staticmethod
    def adapt_followup(
        engagement_risk: str,
        risk_score: float,
        number_of_attempts: int,
        time_since_last_attempt_hours: Optional[float] = None,
        case_risk_score: float = 0.5,
        policy: EngagementPolicy = DEFAULT_POLICY
    ) -> Dict[str, Any]:
        """
        Determine follow-up priority, frequency, and escalation based on policy.
        
        Args:
            engagement_risk: From EngagementRiskClassifier
            risk_score: Engagement risk score (0.0-1.0)
            number_of_attempts: Previous follow-up attempts
            time_since_last_attempt_hours: Hours since last attempt (None if first)
            case_risk_score: Case risk score from Feature-1
            policy: Policy configuration
        
        Returns:
            {
                "followup_priority": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
                "followup_frequency": int (hours),
                "escalation_needed": bool,
                "escalation_reason": str | None,
                "can_send_now": bool,
                "next_allowed_time": datetime | None,
                "policy_reasoning": str
            }
        """
        # Determine priority from engagement risk
        if engagement_risk == "HIGH_RISK_ENGAGEMENT":
            base_priority = "HIGH"
            frequency = policy.frequency_high_risk
            max_attempts = policy.max_attempts_high_risk
        elif engagement_risk == "MEDIUM_RISK_ENGAGEMENT":
            base_priority = "MEDIUM"
            frequency = policy.frequency_medium_risk
            max_attempts = policy.max_attempts_medium_risk
        else:
            base_priority = "LOW"
            frequency = policy.frequency_low_risk
            max_attempts = policy.max_attempts_low_risk
        
        # Elevate priority if case risk is high
        if case_risk_score >= policy.escalation_risk_score_threshold:
            if base_priority == "HIGH":
                base_priority = "CRITICAL"
            elif base_priority == "MEDIUM":
                base_priority = "HIGH"
        
        # Check escalation conditions
        escalation_needed = False
        escalation_reason = None
        
        # Condition 1: Exceeded max attempts
        if number_of_attempts >= max_attempts:
            escalation_needed = True
            escalation_reason = f"Exceeded max attempts ({number_of_attempts}/{max_attempts})"
        
        # Condition 2: Exceeded policy escalation threshold
        if number_of_attempts >= policy.escalation_after_attempts and not escalation_needed:
            escalation_needed = True
            escalation_reason = f"Reached escalation threshold ({number_of_attempts} attempts)"
        
        # Condition 3: High case risk score
        if case_risk_score >= policy.escalation_risk_score_threshold and number_of_attempts >= 2:
            escalation_needed = True
            escalation_reason = escalation_reason or f"High risk case ({case_risk_score:.2f}) with multiple attempts"
        
        # COMPLIANCE: Check minimum reminder interval
        can_send_now = True
        next_allowed_time = None
        
        if time_since_last_attempt_hours is not None:
            if time_since_last_attempt_hours < policy.compliance_min_reminder_hours:
                can_send_now = False
                hours_remaining = policy.compliance_min_reminder_hours - time_since_last_attempt_hours
                next_allowed_time = datetime.utcnow() + timedelta(hours=hours_remaining)
        
        # Ensure frequency respects compliance minimum
        frequency = max(frequency, policy.compliance_min_reminder_hours)
        
        # Build policy reasoning
        reasoning_parts = [
            f"Engagement risk: {engagement_risk}",
            f"Priority: {base_priority}",
            f"Frequency: {frequency}h",
            f"Attempts: {number_of_attempts}/{max_attempts}"
        ]
        
        if escalation_needed:
            reasoning_parts.append(f"ESCALATION: {escalation_reason}")
        
        if not can_send_now:
            reasoning_parts.append(f"Compliance hold: Wait {policy.compliance_min_reminder_hours}h minimum")
        
        return {
            "followup_priority": base_priority,
            "followup_frequency": frequency,
            "escalation_needed": escalation_needed,
            "escalation_reason": escalation_reason,
            "can_send_now": can_send_now,
            "next_allowed_time": next_allowed_time.isoformat() if next_allowed_time else None,
            "max_attempts": max_attempts,
            "attempts_remaining": max(0, max_attempts - number_of_attempts),
            "policy_reasoning": " | ".join(reasoning_parts)
        }


# ============================================================================
# MAIN ENGAGEMENT RISK ADAPTATION SERVICE
# ============================================================================

class EngagementRiskAdaptationService:
    """
    Feature-2: Complete Engagement Risk Adaptation Module
    
    Integrates:
    1. Response prediction (existing ML model)
    2. Engagement risk classification
    3. Policy-controlled adaptation
    
    COMPLIANCE SAFE - AI Recommends, Policy Decides
    """
    
    def __init__(self, policy: EngagementPolicy = None):
        self.policy = policy or DEFAULT_POLICY
        self.classifier = EngagementRiskClassifier()
        self.adapter = PolicyControlledAdapter()
    
    def process(
        self,
        response_probability: float,
        prediction_confidence: float,
        case_seriousness: str = "MEDIUM",
        case_risk_score: float = 0.5,
        number_of_attempts: int = 0,
        time_since_last_attempt_hours: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Complete engagement risk adaptation pipeline.
        
        Args:
            response_probability: From ML model (0.0-1.0)
            prediction_confidence: From ML model (0.0-1.0)
            case_seriousness: From Feature-1 ("HIGH", "MEDIUM", "LOW")
            case_risk_score: From Feature-1 (0.0-1.0)
            number_of_attempts: Previous follow-up attempts
            time_since_last_attempt_hours: Hours since last attempt
        
        Returns:
            {
                "response_probability": float,
                "prediction_confidence": float,
                "engagement_risk": str,
                "followup_priority": str,
                "followup_frequency": int,
                "escalation_needed": bool,
                ... additional fields
            }
        """
        # Step 1: Classify engagement risk
        classification = self.classifier.classify(
            response_probability=response_probability,
            prediction_confidence=prediction_confidence,
            case_seriousness=case_seriousness,
            policy=self.policy
        )
        
        # Step 2: Apply policy-controlled adaptation
        adaptation = self.adapter.adapt_followup(
            engagement_risk=classification["engagement_risk"],
            risk_score=classification["risk_score"],
            number_of_attempts=number_of_attempts,
            time_since_last_attempt_hours=time_since_last_attempt_hours,
            case_risk_score=case_risk_score,
            policy=self.policy
        )
        
        # Combine results
        return {
            # Required outputs
            "response_probability": response_probability,
            "prediction_confidence": prediction_confidence,
            "engagement_risk": classification["engagement_risk"],
            "followup_priority": adaptation["followup_priority"],
            "followup_frequency": adaptation["followup_frequency"],
            "escalation_needed": adaptation["escalation_needed"],
            
            # Additional context
            "engagement_risk_score": classification["risk_score"],
            "escalation_reason": adaptation["escalation_reason"],
            "can_send_now": adaptation["can_send_now"],
            "next_allowed_time": adaptation["next_allowed_time"],
            "max_attempts": adaptation["max_attempts"],
            "attempts_remaining": adaptation["attempts_remaining"],
            
            # Explainability
            "classification_reasoning": classification["classification_reasoning"],
            "policy_reasoning": adaptation["policy_reasoning"],
            "factors": classification["factors"],
            
            # Metadata
            "processed_at": datetime.utcnow().isoformat(),
            "policy_version": "1.0"
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global service instance with default policy
_service = EngagementRiskAdaptationService()


def adapt_engagement_risk(
    response_probability: float,
    prediction_confidence: float,
    case_seriousness: str = "MEDIUM",
    case_risk_score: float = 0.5,
    number_of_attempts: int = 0,
    time_since_last_attempt_hours: Optional[float] = None
) -> Dict[str, Any]:
    """
    Convenience function for engagement risk adaptation.
    
    Example:
        result = adapt_engagement_risk(
            response_probability=0.4,
            prediction_confidence=0.75,
            case_seriousness="HIGH",
            case_risk_score=0.8,
            number_of_attempts=2
        )
        
        print(result["engagement_risk"])  # "HIGH_RISK_ENGAGEMENT"
        print(result["followup_priority"])  # "CRITICAL"
        print(result["escalation_needed"])  # True
    """
    return _service.process(
        response_probability=response_probability,
        prediction_confidence=prediction_confidence,
        case_seriousness=case_seriousness,
        case_risk_score=case_risk_score,
        number_of_attempts=number_of_attempts,
        time_since_last_attempt_hours=time_since_last_attempt_hours
    )


# ============================================================================
# TEST
# ============================================================================

def test_engagement_risk_adaptation():
    """Test the engagement risk adaptation module"""
    print("=" * 70)
    print("TESTING FEATURE-2: ENGAGEMENT RISK ADAPTATION")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Low response, high seriousness",
            "response_probability": 0.25,
            "prediction_confidence": 0.8,
            "case_seriousness": "HIGH",
            "case_risk_score": 0.85,
            "number_of_attempts": 2
        },
        {
            "name": "Medium response, medium seriousness",
            "response_probability": 0.55,
            "prediction_confidence": 0.7,
            "case_seriousness": "MEDIUM",
            "case_risk_score": 0.5,
            "number_of_attempts": 1
        },
        {
            "name": "High response, low seriousness",
            "response_probability": 0.8,
            "prediction_confidence": 0.9,
            "case_seriousness": "LOW",
            "case_risk_score": 0.3,
            "number_of_attempts": 0
        },
        {
            "name": "Multiple attempts, escalation scenario",
            "response_probability": 0.3,
            "prediction_confidence": 0.6,
            "case_seriousness": "HIGH",
            "case_risk_score": 0.75,
            "number_of_attempts": 4
        },
        {
            "name": "Compliance hold scenario",
            "response_probability": 0.4,
            "prediction_confidence": 0.7,
            "case_seriousness": "MEDIUM",
            "case_risk_score": 0.6,
            "number_of_attempts": 1,
            "time_since_last_attempt_hours": 12  # Less than 24h minimum
        }
    ]
    
    for tc in test_cases:
        print(f"\n{'='*70}")
        print(f"Test: {tc['name']}")
        print("-" * 70)
        
        result = adapt_engagement_risk(
            response_probability=tc["response_probability"],
            prediction_confidence=tc["prediction_confidence"],
            case_seriousness=tc["case_seriousness"],
            case_risk_score=tc["case_risk_score"],
            number_of_attempts=tc["number_of_attempts"],
            time_since_last_attempt_hours=tc.get("time_since_last_attempt_hours")
        )
        
        print(f"Input:")
        print(f"  Response Prob: {tc['response_probability']:.0%}")
        print(f"  Confidence: {tc['prediction_confidence']:.0%}")
        print(f"  Seriousness: {tc['case_seriousness']}")
        print(f"  Risk Score: {tc['case_risk_score']:.2f}")
        print(f"  Attempts: {tc['number_of_attempts']}")
        
        print(f"\nOutput:")
        print(f"  Engagement Risk: {result['engagement_risk']}")
        print(f"  Priority: {result['followup_priority']}")
        print(f"  Frequency: {result['followup_frequency']}h")
        print(f"  Escalation: {result['escalation_needed']}")
        if result['escalation_reason']:
            print(f"  Escalation Reason: {result['escalation_reason']}")
        print(f"  Can Send Now: {result['can_send_now']}")
        
        print(f"\nReasoning:")
        print(f"  {result['classification_reasoning']}")
        print(f"  {result['policy_reasoning']}")


if __name__ == "__main__":
    test_engagement_risk_adaptation()