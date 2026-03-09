"""
COMPLETE FEATURE #3 - Integration & Demo
Question Value Scoring + Adaptive Stopping
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from question_value_scorer import QuestionValueScorer
from typing import Dict, List, Any


class AdaptiveQuestioningSystem:
    """
    Complete system that:
    1. Scores questions by value
    2. Detects when to stop (confidence reached)
    3. Prevents redundant questions (diminishing returns)
    4. Maximizes information gain
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.85,
        ev_threshold: float = 0.15,
        max_questions_per_round: int = 5,
        max_rounds: int = 3
    ):
        self.confidence_threshold = confidence_threshold
        self.ev_threshold = ev_threshold
        self.max_questions = max_questions_per_round
        self.max_rounds = max_rounds
        self.scorer = QuestionValueScorer()
    
    def should_continue_questioning(
        self,
        current_confidence: float,
        last_info_gain: float = None,
        round_number: int = 1,
        questions_remaining: int = 0
    ) -> Dict[str, Any]:
        """
        ADAPTIVE STOPPING: Decide if we should ask more questions
        
        Returns dict with:
        - continue: bool
        - reason: str
        - explanation: str
        """
        # Rule 1: Confidence threshold reached ✓
        if current_confidence >= self.confidence_threshold:
            return {
                'continue': False,
                'reason': 'CONFIDENCE_THRESHOLD_REACHED',
                'explanation': f'Safety confidence {current_confidence:.1%} meets threshold {self.confidence_threshold:.1%}',
                'success': True
            }
        
        # Rule 2: No high-value questions left
        if questions_remaining == 0:
            return {
                'continue': False,
                'reason': 'NO_HIGH_VALUE_QUESTIONS',
                'explanation': f'No questions exceed EV threshold {self.ev_threshold}',
                'success': False
            }
        
        # Rule 3: Diminishing returns ✓
        if last_info_gain is not None and last_info_gain < 0.02:
            return {
                'continue': False,
                'reason': 'DIMINISHING_RETURNS',
                'explanation': f'Last round gained only {last_info_gain:.1%} confidence',
                'success': False
            }
        
        # Rule 4: Max rounds reached
        if round_number >= self.max_rounds:
            return {
                'continue': False,
                'reason': 'MAX_ROUNDS_REACHED',
                'explanation': f'Reached maximum {self.max_rounds} questioning rounds',
                'success': False
            }
        
        # Continue questioning
        gap = self.confidence_threshold - current_confidence
        return {
            'continue': True,
            'reason': 'BELOW_THRESHOLD',
            'explanation': f'Need {gap:.1%} more confidence. Continue questioning.',
            'gap': round(gap, 3)
        }
    
    def select_questions_for_round(
        self,
        available_questions: List[Dict[str, str]],
        case_state: Dict[str, Any],
        reporter_type: str = 'UNKNOWN'
    ) -> Dict[str, Any]:
        """
        Select which questions to ask this round
        
        Uses VALUE SCORING to prioritize questions
        """
        # Score and rank all questions
        scored = self.scorer.rank_questions(
            available_questions,
            case_state,
            reporter_type,
            self.max_questions
        )
        
        # Filter by EV threshold
        high_value = [q for q in scored if q['expected_value'] >= self.ev_threshold]
        
        if not high_value:
            return {
                'questions': [],
                'total_expected_value': 0.0,
                'average_ev': 0.0,
                'recommendation': 'STOP',
                'reason': 'No questions exceed EV threshold'
            }
        
        # Calculate metrics
        total_ev = sum(q['expected_value'] for q in high_value)
        avg_ev = total_ev / len(high_value)
        
        return {
            'questions': high_value,
            'total_expected_value': round(total_ev, 2),
            'average_ev': round(avg_ev, 2),
            'recommendation': 'ASK',
            'reason': f'Selected {len(high_value)} high-value questions (avg EV: {avg_ev:.2f})'
        }
    
    def calculate_expected_info_gain(
        self,
        questions: List[Dict[str, Any]]
    ) -> float:
        """
        Estimate how much we'll learn if these questions are answered
        """
        total_gain = 0.0
        
        for q in questions:
            # Expected gain = info_gain × answer_probability
            expected = q['information_gain'] * q['answer_probability']
            total_gain += expected
        
        return round(total_gain, 3)
    
    def run_adaptive_questioning_demo(
        self,
        case_data: Dict[str, Any],
        all_possible_questions: List[Dict[str, str]]
    ):
        """
        DEMO: Complete adaptive questioning workflow
        """
        print("\n" + "="*70)
        print("🎯 ADAPTIVE QUESTIONING SYSTEM DEMO")
        print("="*70)
        
        print(f"\n📋 Case Overview:")
        print(f"   Drug: {case_data.get('drug', 'Unknown')}")
        print(f"   Event: {case_data.get('event', 'Unknown')}")
        print(f"   Reporter: {case_data.get('reporter_type', 'Unknown')}")
        print(f"   Initial Confidence: {case_data.get('confidence', 0.4):.1%}")
        print(f"   Target: {self.confidence_threshold:.1%}")
        
        current_confidence = case_data.get('confidence', 0.4)
        round_number = 0
        history = []
        
        # Questioning rounds
        while round_number < self.max_rounds:
            round_number += 1
            
            print(f"\n{'='*70}")
            print(f"🔄 ROUND {round_number}")
            print(f"{'='*70}")
            
            # Check if should continue
            decision = self.should_continue_questioning(
                current_confidence,
                history[-1]['info_gain'] if history else None,
                round_number,
                len(all_possible_questions)
            )
            
            print(f"\n📊 Current State:")
            print(f"   Confidence: {current_confidence:.1%}")
            print(f"   Decision: {decision['reason']}")
            print(f"   {decision['explanation']}")
            
            if not decision['continue']:
                print(f"\n✅ {decision['explanation']}")
                break
            
            # Select questions for this round
            selection = self.select_questions_for_round(
                all_possible_questions,
                case_data,
                case_data.get('reporter_type', 'UNKNOWN')
            )
            
            if selection['recommendation'] == 'STOP':
                print(f"\n⛔ {selection['reason']}")
                break
            
            questions = selection['questions']
            
            print(f"\n❓ Selected Questions ({len(questions)}):")
            print(f"   Total Expected Value: {selection['total_expected_value']}")
            print(f"   Average EV: {selection['average_ev']:.2f}")
            
            for i, q in enumerate(questions, 1):
                print(f"\n   {i}. [{q['priority']}] {q['question']}")
                print(f"      Field: {q['field']}")
                print(f"      Info Gain: {q['information_gain']:.0%}")
                print(f"      Answer Prob: {q['answer_probability']:.0%}")
                print(f"      Expected Value: {q['expected_value']:.2f}")
            
            # Simulate answers (in real system, would wait for responses)
            answered = int(len(questions) * 0.7)  # 70% answer rate
            info_gain = self.calculate_expected_info_gain(questions[:answered])
            
            print(f"\n📬 Simulated Response:")
            print(f"   Questions Sent: {len(questions)}")
            print(f"   Answers Received: {answered}")
            print(f"   Information Gained: {info_gain:.1%}")
            
            # Update confidence
            current_confidence += info_gain
            current_confidence = min(0.95, current_confidence)
            
            # Record history
            history.append({
                'round': round_number,
                'questions_asked': len(questions),
                'questions_answered': answered,
                'info_gain': info_gain,
                'confidence_after': current_confidence
            })
            
            # Remove asked questions
            asked_fields = [q['field'] for q in questions]
            all_possible_questions = [
                q for q in all_possible_questions 
                if q['field'] not in asked_fields
            ]
        
        # Summary
        print(f"\n{'='*70}")
        print("✅ ADAPTIVE QUESTIONING COMPLETE")
        print(f"{'='*70}")
        
        print(f"\n📊 Summary:")
        print(f"   Rounds: {round_number}")
        print(f"   Initial Confidence: {case_data.get('confidence', 0.4):.1%}")
        print(f"   Final Confidence: {current_confidence:.1%}")
        print(f"   Total Gain: +{current_confidence - case_data.get('confidence', 0.4):.1%}")
        
        if current_confidence >= self.confidence_threshold:
            print(f"\n   🎉 SUCCESS: Reached confidence threshold!")
        else:
            print(f"\n   ⚠️ STOPPED: {decision['reason']}")
        
        total_questions = sum(h['questions_asked'] for h in history)
        total_answered = sum(h['questions_answered'] for h in history)
        
        print(f"\n   Questions Asked: {total_questions}")
        print(f"   Answers Received: {total_answered}")
        print(f"   Response Rate: {total_answered/total_questions:.1%}")
        
        print(f"\n💡 Key Achievements:")
        print(f"   ✓ Value-based question selection")
        print(f"   ✓ Adaptive stopping (didn't over-ask)")
        print(f"   ✓ Diminishing returns detection")
        print(f"   ✓ Confidence-driven workflow")


# Demo execution
if __name__ == "__main__":
    # Sample case
    case = {
        'drug': 'KYNMOBI',
        'event': 'Dyspepsia',
        'reporter_type': 'HP',
        'confidence': 0.45,
        'completeness': 0.60,
        'risk_score': 0.35,
        'missing_count': 4
    }
    
    # Sample questions
    questions = [
        {'field': 'patient_age', 'question': 'What was the patient\'s age?', 'complexity': 'simple'},
        {'field': 'patient_sex', 'question': 'What was the patient\'s sex?', 'complexity': 'simple'},
        {'field': 'event_date', 'question': 'When did the adverse event occur?', 'complexity': 'moderate'},
        {'field': 'drug_dose', 'question': 'What dose was administered?', 'complexity': 'moderate'},
        {'field': 'concomitant_drugs', 'question': 'Were any other drugs taken?', 'complexity': 'complex'},
        {'field': 'medical_history', 'question': 'Any relevant medical history?', 'complexity': 'complex'},
        {'field': 'event_outcome', 'question': 'What was the outcome?', 'complexity': 'moderate'},
    ]
    
    # Run demo
    system = AdaptiveQuestioningSystem(
        confidence_threshold=0.85,
        ev_threshold=0.15,
        max_questions_per_round=3,
        max_rounds=3
    )
    
    system.run_adaptive_questioning_demo(case, questions)
