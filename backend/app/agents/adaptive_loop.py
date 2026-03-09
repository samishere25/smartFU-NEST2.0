"""
Adaptive Loop Orchestration Engine
Continuously iterates until safety confidence threshold is reached
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime, timedelta
import uuid

from app.agents.graph import smartfu_agent
from app.db.session import SessionLocal
from app.models.case import AECase
# from app.models.followup import FollowUpAttempt, CaseConfidenceHistory, AdaptiveLoopSession
from app.utils.safety_confidence import SafetyConfidenceCalculator


class AdaptiveLoopEngine:
    """
    Orchestrates the adaptive follow-up loop
    Iterates until confidence threshold or max attempts
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.85,
        max_iterations: int = 3,
        min_information_gain: float = 0.02
    ):
        self.confidence_threshold = confidence_threshold
        self.max_iterations = max_iterations
        self.min_information_gain = min_information_gain
        self.confidence_calculator = SafetyConfidenceCalculator()
    
    async def run_adaptive_loop(
        self,
        case_id: str,
        db: SessionLocal,
        simulate_responses: bool = False
    ) -> Dict[str, Any]:
        """
        Main adaptive loop
        
        Args:
            case_id: Case to analyze
            db: Database session
            simulate_responses: If True, simulate reporter responses for demo
        
        Returns:
            Complete analysis with iteration history
        """
        print("\n" + "="*70)
        print("🔄 ADAPTIVE LOOP ENGINE STARTED")
        print("="*70)
        
        # Load case
        case = db.query(AECase).filter(AECase.case_id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Create session tracking
        session = {
            'session_id': str(uuid.uuid4()),
            'case_id': case_id,
            'started_at': datetime.utcnow(),
            'iterations': [],
            'converged': False,
            'convergence_reason': None
        }
        
        # Initial case state
        current_state = self._prepare_case_state(case)
        iteration = 0
        
        print(f"\n📋 Case: {case.suspect_drug} - {case.adverse_event}")
        print(f"   Reporter: {case.reporter_type}, Age: {case.patient_age}")
        
        # === ADAPTIVE LOOP ===
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n{'='*70}")
            print(f"🔄 ITERATION {iteration} / {self.max_iterations}")
            print(f"{'='*70}")
            
            # Run AI analysis
            iteration_result = await self._run_iteration(
                current_state, iteration, db
            )
            
            # Store iteration
            session['iterations'].append(iteration_result)
            
            # Check if we should continue
            should_continue = self.confidence_calculator.should_continue_followup(
                current_confidence=iteration_result['confidence_metrics']['overall_confidence'],
                iteration_number=iteration,
                last_information_gain=iteration_result.get('information_gain', 0),
                max_iterations=self.max_iterations
            )
            
            print(f"\n📊 Iteration {iteration} Results:")
            print(f"   Safety Confidence: {iteration_result['confidence_metrics']['overall_confidence']:.1%}")
            print(f"   Decision: {should_continue['reason']}")
            print(f"   Continue? {'YES' if should_continue['continue'] else 'NO'}")
            
            if not should_continue['continue']:
                session['converged'] = True
                session['convergence_reason'] = should_continue['reason']
                session['convergence_explanation'] = should_continue['explanation']
                print(f"\n✅ {should_continue['explanation']}")
                break
            
            # If simulating, generate mock response
            if simulate_responses and iteration_result['questions']:
                print(f"\n🤖 Simulating reporter response...")
                response_data = self._simulate_response(iteration_result['questions'])
                
                # Update case state with new information
                current_state = self._update_state_with_response(
                    current_state, response_data
                )
                
                print(f"   ✓ Filled {len(response_data)} fields")
            else:
                # In production, would wait for actual response
                print(f"\n⏳ Waiting for reporter response...")
                print(f"   (In production, this would pause until response received)")
                break  # For demo, stop here
        
        # Complete session
        session['completed_at'] = datetime.utcnow()
        session['total_iterations'] = iteration
        session['final_confidence'] = iteration_result['confidence_metrics']['overall_confidence']
        
        # Calculate summary metrics
        session['summary'] = self._calculate_session_summary(session)
        
        self._print_final_summary(session)
        
        return session
    
    async def _run_iteration(
        self,
        state: Dict[str, Any],
        iteration: int,
        db: SessionLocal
    ) -> Dict[str, Any]:
        """Run one iteration of analysis"""
        
        # Run AI agents
        result = await smartfu_agent(state)
        
        # Calculate confidence metrics
        confidence_metrics = self.confidence_calculator.calculate_overall_confidence(
            case_data=state['case_data'],
            missing_fields=result.get('missing_fields', []),
            risk_score=result.get('risk_score', 0.0),
            response_probability=result.get('response_probability', 0.0),
            past_attempts=iteration - 1
        )
        
        # Calculate information gain (if not first iteration)
        information_gain = 0.0
        if iteration > 1 and hasattr(state, 'previous_confidence'):
            information_gain = confidence_metrics['overall_confidence'] - state['previous_confidence']
        
        iteration_result = {
            'iteration': iteration,
            'timestamp': datetime.utcnow().isoformat(),
            'analysis': result,
            'confidence_metrics': confidence_metrics,
            'information_gain': information_gain,
            'questions': result.get('questions', []),
            'decision': result.get('decision', 'UNKNOWN')
        }
        
        # Store current confidence for next iteration
        state['previous_confidence'] = confidence_metrics['overall_confidence']
        
        return iteration_result
    
    def _prepare_case_state(self, case: AECase) -> Dict[str, Any]:
        """Prepare initial case state"""
        return {
            'case_id': str(case.case_id),
            'case_data': {
                'suspect_drug': case.suspect_drug,
                'adverse_event': case.adverse_event,
                'patient_age': case.patient_age,
                'patient_sex': case.patient_sex,
                'drug_route': case.drug_route,
                'drug_dose': case.drug_dose,
                'reporter_type': case.reporter_type,
                'event_date': None
            },
            'missing_fields': [],
            'risk_score': 0.0,
            'response_probability': 0.0,
            'decision': '',
            'questions': [],
            'reasoning': '',
            'messages': [],
            'previous_confidence': 0.0
        }
    
    def _simulate_response(self, questions: List[Dict]) -> Dict[str, Any]:
        """
        Simulate reporter response (for demo/testing)
        In production, this would come from actual reporter
        """
        import random
        
        responses = {}
        
        for q in questions[:2]:  # Simulate answering first 2 questions
            field = q.get('field', '')
            
            # Generate mock responses based on field
            if field == 'patient_age':
                responses[field] = random.randint(50, 80)
            elif field == 'patient_sex':
                responses[field] = random.choice(['M', 'F'])
            elif field == 'drug_dose':
                responses[field] = f"{random.randint(10, 500)}mg"
            elif field == 'drug_route':
                responses[field] = random.choice(['ORAL', 'IV', 'IM'])
            elif field == 'event_date':
                responses[field] = '2024-01-15'
            else:
                responses[field] = "Patient experienced symptoms after 3 days"
        
        return responses
    
    def _update_state_with_response(
        self,
        state: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update case state with new information from response"""
        
        # Update case data
        for field, value in response_data.items():
            state['case_data'][field] = value
        
        # Remove from missing fields
        state['missing_fields'] = [
            f for f in state['missing_fields']
            if f not in response_data
        ]
        
        return state
    
    def _calculate_session_summary(self, session: Dict) -> Dict[str, Any]:
        """Calculate summary metrics for the session"""
        
        if not session['iterations']:
            return {}
        
        first = session['iterations'][0]
        last = session['iterations'][-1]
        
        initial_conf = first['confidence_metrics']['overall_confidence']
        final_conf = last['confidence_metrics']['overall_confidence']
        
        total_questions = sum(
            len(it['questions']) for it in session['iterations']
        )
        
        total_gain = final_conf - initial_conf
        gain_per_iteration = total_gain / len(session['iterations']) if session['iterations'] else 0
        
        return {
            'total_iterations': len(session['iterations']),
            'initial_confidence': round(initial_conf, 3),
            'final_confidence': round(final_conf, 3),
            'total_confidence_gain': round(total_gain, 3),
            'gain_per_iteration': round(gain_per_iteration, 3),
            'total_questions_asked': total_questions,
            'converged': session['converged'],
            'convergence_reason': session.get('convergence_reason'),
            'efficiency_rating': self.confidence_calculator._rate_efficiency(gain_per_iteration),
            'duration_seconds': (
                session['completed_at'] - session['started_at']
            ).total_seconds() if 'completed_at' in session else 0
        }
    
    def _print_final_summary(self, session: Dict):
        """Print final summary of adaptive loop"""
        
        summary = session['summary']
        
        print("\n" + "="*70)
        print("✅ ADAPTIVE LOOP COMPLETE")
        print("="*70)
        
        print(f"\n📊 Summary:")
        print(f"   Total Iterations: {summary['total_iterations']}")
        print(f"   Initial Confidence: {summary['initial_confidence']:.1%}")
        print(f"   Final Confidence: {summary['final_confidence']:.1%}")
        print(f"   Confidence Gain: +{summary['total_confidence_gain']:.1%}")
        print(f"   Gain per Iteration: {summary['gain_per_iteration']:.1%}")
        print(f"   Questions Asked: {summary['total_questions_asked']}")
        print(f"   Converged: {summary['converged']}")
        print(f"   Reason: {summary.get('convergence_reason', 'N/A')}")
        print(f"   Efficiency: {summary['efficiency_rating']}")
        print(f"   Duration: {summary['duration_seconds']:.1f}s")
        
        print("\n" + "="*70)


# Convenience function
async def run_adaptive_analysis(
    case_id: str,
    db: SessionLocal,
    simulate_responses: bool = True
) -> Dict[str, Any]:
    """
    Quick access to adaptive loop analysis
    
    Args:
        case_id: Case to analyze
        db: Database session
        simulate_responses: Simulate responses for demo
    
    Returns:
        Complete analysis with iteration history
    """
    engine = AdaptiveLoopEngine(
        confidence_threshold=0.85,
        max_iterations=3,
        min_information_gain=0.02
    )
    
    return await engine.run_adaptive_loop(case_id, db, simulate_responses)
