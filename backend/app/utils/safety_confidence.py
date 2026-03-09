"""
Safety Confidence Calculator
Quantifies how confident we are in the safety assessment
"""

from typing import Dict, List, Any
import math


class SafetyConfidenceCalculator:
    """
    Calculates safety confidence based on:
    1. Data completeness
    2. Risk assessment certainty
    3. Response prediction reliability
    4. Historical validation
    """
    
    # Critical fields for safety assessment
    CRITICAL_FIELDS = [
        'patient_age',
        'patient_sex',
        'drug_dose',
        'event_date',
        'adverse_event',
        'suspect_drug',
        'reporter_type'
    ]
    
    # Important but not critical
    IMPORTANT_FIELDS = [
        'drug_route',
        'concomitant_drugs',
        'medical_history',
        'event_outcome'
    ]
    
    def __init__(self):
        self.min_confidence_threshold = 0.85  # 85% confidence to proceed
        self.critical_field_weight = 0.15     # Each critical field worth 15%
        self.important_field_weight = 0.05    # Each important field worth 5%
    
    def calculate_data_completeness_confidence(
        self, 
        case_data: Dict[str, Any],
        missing_fields: List[str]
    ) -> float:
        """
        Calculate confidence based on data completeness
        
        Returns:
            float: 0.0-1.0 confidence score
        """
        # Start with base confidence
        confidence = 0.0
        
        # Check critical fields
        critical_present = 0
        critical_total = len(self.CRITICAL_FIELDS)
        
        for field in self.CRITICAL_FIELDS:
            value = case_data.get(field)
            if value is not None and value != '' and value != 'UNKNOWN':
                critical_present += 1
        
        # Critical fields contribute 70% of confidence
        critical_confidence = (critical_present / critical_total) * 0.70
        
        # Check important fields
        important_present = 0
        important_total = len(self.IMPORTANT_FIELDS)
        
        for field in self.IMPORTANT_FIELDS:
            value = case_data.get(field)
            if value is not None and value != '' and value != 'UNKNOWN':
                important_present += 1
        
        # Important fields contribute 30% of confidence
        important_confidence = (important_present / important_total) * 0.30
        
        confidence = critical_confidence + important_confidence
        
        return min(1.0, max(0.0, confidence))
    
    def calculate_risk_assessment_confidence(
        self,
        risk_score: float,
        data_completeness: float
    ) -> float:
        """
        Calculate confidence in risk assessment
        
        High risk + incomplete data = low confidence
        Low risk + complete data = high confidence
        """
        # Base confidence from data completeness
        base = data_completeness
        
        # Adjust based on risk level
        # High risk cases need more complete data
        if risk_score > 0.7:  # High risk
            # Require > 80% completeness for high confidence
            if data_completeness < 0.80:
                penalty = (0.80 - data_completeness) * 0.5
                base -= penalty
        elif risk_score > 0.5:  # Medium risk
            # Require > 60% completeness
            if data_completeness < 0.60:
                penalty = (0.60 - data_completeness) * 0.3
                base -= penalty
        else:  # Low risk
            # More tolerant of missing data
            base = min(1.0, base + 0.1)
        
        return min(1.0, max(0.0, base))
    
    def calculate_response_reliability(
        self,
        response_probability: float,
        reporter_credibility: float,
        past_attempts: int = 0
    ) -> float:
        """
        How reliable is our response prediction?
        """
        # Base reliability from ML model
        base = 0.7  # Our model has 70% accuracy
        
        # Adjust for reporter credibility
        base += (reporter_credibility - 0.5) * 0.2
        
        # Decrease confidence if multiple failed attempts
        if past_attempts > 0:
            penalty = past_attempts * 0.15
            base -= penalty
        
        # Multiply by response probability
        reliability = base * response_probability
        
        return min(1.0, max(0.0, reliability))
    
    def calculate_overall_confidence(
        self,
        case_data: Dict[str, Any],
        missing_fields: List[str],
        risk_score: float,
        response_probability: float,
        reporter_credibility: float = 0.7,
        past_attempts: int = 0
    ) -> Dict[str, float]:
        """
        Calculate overall safety confidence
        
        Returns dict with:
        - data_completeness_confidence
        - risk_assessment_confidence
        - response_reliability
        - overall_confidence
        - can_proceed (bool)
        """
        # Individual confidences
        data_conf = self.calculate_data_completeness_confidence(
            case_data, missing_fields
        )
        
        risk_conf = self.calculate_risk_assessment_confidence(
            risk_score, data_conf
        )
        
        response_rel = self.calculate_response_reliability(
            response_probability, reporter_credibility, past_attempts
        )
        
        # Overall confidence (weighted average)
        # Data completeness: 50%
        # Risk assessment: 30%
        # Response reliability: 20%
        overall = (
            data_conf * 0.50 +
            risk_conf * 0.30 +
            response_rel * 0.20
        )
        
        return {
            'data_completeness_confidence': round(data_conf, 3),
            'risk_assessment_confidence': round(risk_conf, 3),
            'response_reliability': round(response_rel, 3),
            'overall_confidence': round(overall, 3),
            'can_proceed': overall >= self.min_confidence_threshold,
            'threshold': self.min_confidence_threshold,
            'gap_to_threshold': round(max(0, self.min_confidence_threshold - overall), 3)
        }
    
    def calculate_information_gain(
        self,
        before_confidence: float,
        after_confidence: float,
        questions_asked: int
    ) -> Dict[str, float]:
        """
        How much did we learn from the follow-up?
        """
        gain = after_confidence - before_confidence
        gain_per_question = gain / max(1, questions_asked) if questions_asked > 0 else 0
        
        # Determine if it was worthwhile
        worthwhile = gain_per_question > 0.05  # At least 5% gain per question
        
        return {
            'total_gain': round(gain, 3),
            'gain_per_question': round(gain_per_question, 3),
            'questions_asked': questions_asked,
            'worthwhile': worthwhile,
            'efficiency_rating': self._rate_efficiency(gain_per_question)
        }
    
    def _rate_efficiency(self, gain_per_question: float) -> str:
        """Rate the efficiency of information gathering"""
        if gain_per_question >= 0.15:
            return "EXCELLENT"
        elif gain_per_question >= 0.10:
            return "GOOD"
        elif gain_per_question >= 0.05:
            return "MODERATE"
        elif gain_per_question >= 0.02:
            return "POOR"
        else:
            return "NEGLIGIBLE"
    
    def should_continue_followup(
        self,
        current_confidence: float,
        iteration_number: int,
        last_information_gain: float = None,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Decide if we should continue with more follow-ups
        
        Returns:
            dict with continue (bool) and reason (str)
        """
        # Check 1: Confidence threshold reached
        if current_confidence >= self.min_confidence_threshold:
            return {
                'continue': False,
                'reason': 'CONFIDENCE_THRESHOLD_REACHED',
                'explanation': f'Safety confidence {current_confidence:.1%} exceeds threshold {self.min_confidence_threshold:.1%}'
            }
        
        # Check 2: Max iterations reached
        if iteration_number >= max_iterations:
            return {
                'continue': False,
                'reason': 'MAX_ITERATIONS_REACHED',
                'explanation': f'Reached maximum {max_iterations} follow-up attempts'
            }
        
        # Check 3: Diminishing returns
        if last_information_gain is not None and last_information_gain < 0.02:
            return {
                'continue': False,
                'reason': 'DIMINISHING_RETURNS',
                'explanation': f'Last iteration gained only {last_information_gain:.1%} confidence - not worthwhile to continue'
            }
        
        # Check 4: Very low confidence and early iterations - definitely continue
        if current_confidence < 0.50 and iteration_number < 2:
            return {
                'continue': True,
                'reason': 'LOW_CONFIDENCE',
                'explanation': f'Confidence {current_confidence:.1%} is too low - must continue',
                'urgency': 'HIGH'
            }
        
        # Check 5: Medium confidence - continue if not too many attempts
        if current_confidence < 0.75:
            return {
                'continue': True,
                'reason': 'MODERATE_CONFIDENCE',
                'explanation': f'Confidence {current_confidence:.1%} approaching threshold - one more attempt',
                'urgency': 'MEDIUM'
            }
        
        # Default: Continue with caution
        return {
            'continue': True,
            'reason': 'APPROACHING_THRESHOLD',
            'explanation': f'Confidence {current_confidence:.1%} close to threshold - final attempt',
            'urgency': 'LOW'
        }


# Convenience function
def calculate_safety_confidence(
    case_data: Dict[str, Any],
    missing_fields: List[str],
    risk_score: float,
    response_probability: float,
    **kwargs
) -> Dict[str, float]:
    """Quick access to confidence calculation"""
    calculator = SafetyConfidenceCalculator()
    return calculator.calculate_overall_confidence(
        case_data, missing_fields, risk_score, response_probability, **kwargs
    )
