"""
Question Value Scorer
Calculates the value of each question based on information gain
"""

from typing import Dict, List, Any
import math


class QuestionValueScorer:
    """
    Scores questions based on:
    1. Information gain (how much does it reduce uncertainty?)
    2. Answer probability (how likely to get answered?)
    3. Safety impact (how much does it affect risk assessment?)
    4. Cost (burden on reporter)
    """
    
    # Field importance weights for safety assessment
    FIELD_IMPORTANCE = {
        # Critical fields (highest impact)
        'patient_age': 0.90,
        'event_date': 0.85,
        'drug_dose': 0.85,
        'event_outcome': 0.80,
        'concomitant_drugs': 0.75,
        
        # Important fields
        'patient_sex': 0.70,
        'drug_route': 0.65,
        'medical_history': 0.65,
        'event_duration': 0.60,
        'rechallenge_result': 0.60,
        
        # Supporting fields
        'patient_weight': 0.50,
        'indication': 0.45,
        'dose_frequency': 0.45,
        'time_to_onset': 0.40,
        
        # Context fields
        'reporter_name': 0.30,
        'reporter_address': 0.25,
        'other_info': 0.20
    }
    
    # Question complexity (effort to answer)
    QUESTION_COMPLEXITY = {
        'simple': 0.2,    # Yes/No, single value
        'moderate': 0.5,  # Date, number, short text
        'complex': 0.8,   # Detailed description, multiple items
        'difficult': 1.0  # Requires research/lookup
    }
    
    def calculate_information_gain(
        self,
        field: str,
        current_completeness: float,
        current_risk_uncertainty: float
    ) -> float:
        """
        Calculate how much information we gain by asking this question
        
        Uses entropy reduction formula:
        IG = H(before) - H(after)
        """
        # Base information gain from field importance
        field_weight = self.FIELD_IMPORTANCE.get(field, 0.30)
        
        # Adjust for current completeness
        # More valuable when we have less info
        completeness_factor = 1.0 - current_completeness
        
        # Adjust for risk uncertainty
        # More valuable when risk is uncertain
        uncertainty_factor = current_risk_uncertainty
        
        # Calculate information gain (0-1 scale)
        information_gain = field_weight * (
            0.5 * completeness_factor +
            0.5 * uncertainty_factor
        )
        
        return min(1.0, information_gain)
    
    def estimate_answer_probability(
        self,
        field: str,
        reporter_type: str,
        question_complexity: str = 'moderate'
    ) -> float:
        """
        Estimate probability of getting this question answered
        
        Based on:
        - Reporter type (MD more responsive than CN)
        - Question complexity (simple more likely answered)
        - Field type (some fields easier to provide)
        """
        # Base rates by reporter type
        base_rates = {
            'MD': 0.70,
            'HP': 0.65,
            'PH': 0.60,
            'CN': 0.35,
            'LW': 0.45,
            'UNKNOWN': 0.40
        }
        
        base_prob = base_rates.get(reporter_type, 0.40)
        
        # Adjust for complexity
        complexity_penalty = self.QUESTION_COMPLEXITY.get(
            question_complexity, 0.5
        )
        
        # Adjust for field type
        # Some fields are easier to provide
        field_ease = {
            'patient_age': 1.0,      # Easy
            'patient_sex': 1.0,      # Easy
            'event_date': 0.9,       # Usually known
            'drug_dose': 0.8,        # May need to look up
            'medical_history': 0.6,  # Requires detail
            'concomitant_drugs': 0.7 # May need to check
        }
        
        ease_factor = field_ease.get(field, 0.75)
        
        # Calculate final probability
        answer_prob = base_prob * (1.0 - complexity_penalty * 0.3) * ease_factor
        
        return min(0.95, max(0.10, answer_prob))
    
    def calculate_safety_impact(
        self,
        field: str,
        current_risk_score: float,
        missing_critical_fields: int
    ) -> float:
        """
        How much does this field affect safety assessment?
        
        Returns impact score (0-1)
        """
        # Field importance
        importance = self.FIELD_IMPORTANCE.get(field, 0.30)
        
        # Higher impact when:
        # 1. Risk is already high (need more certainty)
        # 2. Many fields missing (each field more valuable)
        
        risk_amplifier = 1.0 + (current_risk_score * 0.5)
        
        scarcity_amplifier = 1.0 + (
            missing_critical_fields / 10.0
        )  # More missing = each more valuable
        
        impact = importance * risk_amplifier * scarcity_amplifier
        
        return min(1.0, impact / 2.0)  # Normalize
    
    def calculate_expected_value(
        self,
        information_gain: float,
        answer_probability: float,
        safety_impact: float,
        cost: float = 0.5
    ) -> float:
        """
        Calculate Expected Value of asking this question
        
        EV = (Information Gain × Answer Probability × Safety Impact) - Cost
        
        Higher EV = more valuable question
        """
        # Benefit = IG × P(answer) × Safety Impact
        benefit = information_gain * answer_probability * safety_impact
        
        # Net expected value
        ev = benefit - (cost * 0.2)  # Cost has lower weight
        
        return max(0.0, ev)
    
    def score_question(
        self,
        field: str,
        question_text: str,
        case_state: Dict[str, Any],
        reporter_type: str = 'UNKNOWN',
        complexity: str = 'moderate'
    ) -> Dict[str, float]:
        """
        Complete scoring of a question
        
        Returns dict with all scores and final value
        """
        # Extract case state
        current_completeness = case_state.get('completeness', 0.5)
        current_risk = case_state.get('risk_score', 0.5)
        missing_count = case_state.get('missing_count', 5)
        
        # Calculate risk uncertainty
        # High when risk is moderate (most uncertain)
        risk_uncertainty = 1.0 - abs(current_risk - 0.5) * 2.0
        
        # Calculate components
        info_gain = self.calculate_information_gain(
            field, current_completeness, risk_uncertainty
        )
        
        answer_prob = self.estimate_answer_probability(
            field, reporter_type, complexity
        )
        
        safety_impact = self.calculate_safety_impact(
            field, current_risk, missing_count
        )
        
        cost = self.QUESTION_COMPLEXITY.get(complexity, 0.5)
        
        expected_value = self.calculate_expected_value(
            info_gain, answer_prob, safety_impact, cost
        )
        
        # Determine if we should ask
        should_ask = expected_value > 0.15  # Threshold
        
        # Priority level
        if expected_value >= 0.40:
            priority = 'CRITICAL'
        elif expected_value >= 0.25:
            priority = 'HIGH'
        elif expected_value >= 0.15:
            priority = 'MEDIUM'
        else:
            priority = 'LOW'
        
        return {
            'field': field,
            'question': question_text,
            'information_gain': round(info_gain, 3),
            'answer_probability': round(answer_prob, 3),
            'safety_impact': round(safety_impact, 3),
            'cost': round(cost, 3),
            'expected_value': round(expected_value, 3),
            'should_ask': should_ask,
            'priority': priority,
            'reasoning': self._explain_score(
                field, info_gain, answer_prob, safety_impact, expected_value
            )
        }
    
    def _explain_score(
        self,
        field: str,
        ig: float,
        ap: float,
        si: float,
        ev: float
    ) -> str:
        """Generate human-readable explanation"""
        
        reasons = []
        
        if ig > 0.6:
            reasons.append(f"High information gain ({ig:.0%})")
        if ap > 0.6:
            reasons.append(f"Likely to be answered ({ap:.0%})")
        if si > 0.6:
            reasons.append(f"Critical for safety ({si:.0%})")
        if ev < 0.15:
            reasons.append(f"Low expected value ({ev:.2f})")
        
        if not reasons:
            reasons.append(f"Moderate value question (EV: {ev:.2f})")
        
        return " | ".join(reasons)
    
    def rank_questions(
        self,
        questions: List[Dict[str, str]],
        case_state: Dict[str, Any],
        reporter_type: str = 'UNKNOWN',
        max_questions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rank and filter questions by value
        
        Returns top N questions sorted by expected value
        """
        scored_questions = []
        
        for q in questions:
            field = q.get('field', 'unknown')
            question_text = q.get('question', '')
            complexity = q.get('complexity', 'moderate')
            
            score = self.score_question(
                field, question_text, case_state, reporter_type, complexity
            )
            
            scored_questions.append(score)
        
        # Sort by expected value (descending)
        scored_questions.sort(key=lambda x: x['expected_value'], reverse=True)
        
        # Filter: only keep questions above threshold
        high_value = [q for q in scored_questions if q['should_ask']]
        
        # Return top N
        return high_value[:max_questions]
    
    def detect_diminishing_returns(
        self,
        previous_scores: List[float],
        threshold: float = 0.02
    ) -> bool:
        """
        Detect if we're getting diminishing returns
        
        Returns True if last question had very low value
        """
        if not previous_scores:
            return False
        
        if len(previous_scores) < 2:
            return False
        
        # Check if improvement is too small
        last_improvement = previous_scores[-1]
        
        if last_improvement < threshold:
            return True
        
        # Check if trend is declining
        if len(previous_scores) >= 3:
            recent = previous_scores[-3:]
            if recent[0] > recent[1] > recent[2]:
                # Declining trend
                if recent[2] < 0.05:
                    return True
        
        return False


# Convenience function
def score_and_rank_questions(
    questions: List[Dict[str, str]],
    case_state: Dict[str, Any],
    reporter_type: str = 'UNKNOWN',
    max_questions: int = 5
) -> List[Dict[str, Any]]:
    """Quick access to question scoring"""
    scorer = QuestionValueScorer()
    return scorer.rank_questions(
        questions, case_state, reporter_type, max_questions
    )
