"""
Test Adaptive Loop Engine
Demonstrates continuous adaptation until confidence threshold
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
from app.db.session import SessionLocal
from app.models.case import AECase
from app.agents.adaptive_loop import AdaptiveLoopEngine
import json


async def test_adaptive_loop():
    """Test the adaptive loop with a real case"""
    
    print("="*70)
    print("TESTING ADAPTIVE LOOP ENGINE")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # Get a case with missing data
        case = db.query(AECase).first()
        
        if not case:
            print("❌ No cases found in database")
            return
        
        print(f"\n📋 Selected Case:")
        print(f"   ID: {case.case_id}")
        print(f"   Drug: {case.suspect_drug}")
        print(f"   Event: {case.adverse_event}")
        print(f"   Reporter: {case.reporter_type}")
        print(f"   Age: {case.patient_age}")
        
        # Run adaptive loop
        engine = AdaptiveLoopEngine(
            confidence_threshold=0.85,  # 85% confidence goal
            max_iterations=3,           # Max 3 follow-up attempts
            min_information_gain=0.02   # Stop if gain < 2%
        )
        
        result = await engine.run_adaptive_loop(
            case_id=str(case.case_id),
            db=db,
            simulate_responses=True  # Simulate responses for demo
        )
        
        # Print detailed results
        print("\n" + "="*70)
        print("📊 DETAILED ITERATION HISTORY")
        print("="*70)
        
        for iteration in result['iterations']:
            print(f"\n🔄 Iteration {iteration['iteration']}:")
            print(f"   Timestamp: {iteration['timestamp']}")
            
            conf = iteration['confidence_metrics']
            print(f"\n   Confidence Breakdown:")
            print(f"      Data Completeness: {conf['data_completeness_confidence']:.1%}")
            print(f"      Risk Assessment: {conf['risk_assessment_confidence']:.1%}")
            print(f"      Response Reliability: {conf['response_reliability']:.1%}")
            print(f"      Overall: {conf['overall_confidence']:.1%}")
            print(f"      Can Proceed? {conf['can_proceed']}")
            print(f"      Gap to Threshold: {conf['gap_to_threshold']:.1%}")
            
            if iteration['information_gain'] > 0:
                print(f"\n   Information Gain: +{iteration['information_gain']:.1%}")
            
            print(f"\n   Decision: {iteration['decision']}")
            print(f"   Questions Generated: {len(iteration['questions'])}")
            
            if iteration['questions']:
                print(f"\n   Questions Asked:")
                for q in iteration['questions'][:3]:
                    print(f"      • {q.get('question', 'N/A')}")
        
        # Save detailed results
        output_file = Path(__file__).parent / "adaptive_loop_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
    finally:
        db.close()


async def test_multiple_scenarios():
    """Test different scenarios"""
    
    print("\n" + "="*70)
    print("TESTING MULTIPLE SCENARIOS")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # Scenario 1: Low initial confidence
        print("\n🧪 Scenario 1: Low Initial Confidence")
        print("-" * 70)
        
        cases = db.query(AECase).limit(3).all()
        
        for i, case in enumerate(cases, 1):
            print(f"\nCase {i}: {case.suspect_drug}")
            
            engine = AdaptiveLoopEngine(
                confidence_threshold=0.85,
                max_iterations=3
            )
            
            result = await engine.run_adaptive_loop(
                case_id=str(case.case_id),
                db=db,
                simulate_responses=True
            )
            
            summary = result['summary']
            print(f"   Initial: {summary['initial_confidence']:.1%}")
            print(f"   Final: {summary['final_confidence']:.1%}")
            print(f"   Gain: +{summary['total_confidence_gain']:.1%}")
            print(f"   Converged: {summary['converged']} ({summary.get('convergence_reason', 'N/A')})")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🚀 Starting Adaptive Loop Tests...\n")
    
    # Test 1: Single case detailed
    asyncio.run(test_adaptive_loop())
    
    # Test 2: Multiple scenarios
    # asyncio.run(test_multiple_scenarios())
    
    print("\n✅ All tests complete!\n")
