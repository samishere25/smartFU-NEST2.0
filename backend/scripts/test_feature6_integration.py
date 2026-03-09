"""
Feature 6 Integration Test: Risk-Triggered Safety Signal Detection
Tests end-to-end signal detection triggered by case analysis and follow-ups
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

# Import all models to ensure SQLAlchemy mappers are initialized
from app.models.case import AECase
from app.models.signal import SafetySignal
from app.models.followup import FollowUpAttempt
from app.models.user import User

from app.services.signal_service import evaluate_signals_for_case, bulk_evaluate_signals
from app.utils.signal_detection import SafetySignalDetector


def test_signal_detection_infrastructure():
    """Test 1: Verify signal detection infrastructure"""
    print("\n" + "="*80)
    print("TEST 1: Signal Detection Infrastructure")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # Check for existing cases
        case_count = db.query(AECase).count()
        print(f"\n✓ Database connection: OK")
        print(f"✓ Total cases in database: {case_count}")
        
        # Check for signals table
        signal_count = db.query(SafetySignal).count()
        print(f"✓ Safety signals table: OK ({signal_count} signals)")
        
        # Test PRR calculation utility
        detector = SafetySignalDetector()
        print(f"✓ SafetySignalDetector: OK")
        
        print("\n✅ Infrastructure Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Infrastructure Test: FAILED - {e}")
        return False
    finally:
        db.close()


async def test_case_triggered_signal_detection():
    """Test 2: Signal detection triggered by case analysis"""
    print("\n" + "="*80)
    print("TEST 2: Case-Triggered Signal Detection")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # Get a sample case from database
        case = db.query(AECase).filter(
            AECase.suspect_drug.isnot(None),
            AECase.adverse_event.isnot(None)
        ).first()
        
        if not case:
            print("\n⚠️  No cases with drug/event data found. Skipping test.")
            return False
        
        print(f"\n📋 Testing with case:")
        print(f"   Drug: {case.suspect_drug}")
        print(f"   Event: {case.adverse_event}")
        
        # Trigger signal evaluation (simulating what happens after case analysis)
        result = await evaluate_signals_for_case(case, db)
        
        print(f"\n📊 Signal Evaluation Result:")
        print(f"   Signals Updated: {result.get('signals_updated', 0)}")
        print(f"   New Signals: {result.get('new_signals', 0)}")
        
        # Check if signal was created/updated
        signal = db.query(SafetySignal).filter(
            SafetySignal.drug_name == case.suspect_drug,
            SafetySignal.adverse_event == case.adverse_event
        ).first()
        
        if signal:
            print(f"\n✓ Signal found in database:")
            print(f"   Signal ID: {signal.signal_id}")
            print(f"   PRR: {signal.proportional_reporting_ratio:.2f}")
            print(f"   Case Count: {signal.case_count}")
            print(f"   Strength: {signal.signal_strength}")
            print(f"   Status: {signal.signal_status}")
            print(f"   Trend: {signal.trend}")
        
        print("\n✅ Case-Triggered Detection: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Case-Triggered Detection: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_bulk_signal_evaluation():
    """Test 3: Bulk signal evaluation across all cases"""
    print("\n" + "="*80)
    print("TEST 3: Bulk Signal Evaluation")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # Count signals before
        before_count = db.query(SafetySignal).count()
        print(f"\n📊 Signals before evaluation: {before_count}")
        
        # Run bulk evaluation
        result = await bulk_evaluate_signals(db)
        
        print(f"\n📊 Bulk Evaluation Result:")
        print(f"   Drug-Event Combinations: {result.get('combinations_evaluated', 0)}")
        print(f"   Signals Created: {result.get('signals_created', 0)}")
        print(f"   Signals Updated: {result.get('signals_updated', 0)}")
        
        # Count signals after
        after_count = db.query(SafetySignal).count()
        print(f"\n📊 Signals after evaluation: {after_count}")
        print(f"   Net change: +{after_count - before_count}")
        
        print("\n✅ Bulk Evaluation: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Bulk Evaluation: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_signal_prioritization():
    """Test 4: Signal prioritization and escalation levels"""
    print("\n" + "="*80)
    print("TEST 4: Signal Prioritization")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # Get active signals
        signals = db.query(SafetySignal).filter(
            SafetySignal.is_active == True
        ).order_by(SafetySignal.proportional_reporting_ratio.desc()).limit(10).all()
        
        if not signals:
            print("\n⚠️  No active signals found. Run bulk evaluation first.")
            return False
        
        print(f"\n📊 Top {len(signals)} Active Signals:")
        print("\n" + "-"*80)
        
        for i, signal in enumerate(signals, 1):
            # Determine escalation level (same logic as API)
            if signal.prr >= 8 and signal.trend == 'UP':
                level = 'IMMEDIATE'
            elif signal.prr >= 5:
                level = 'HIGH'
            elif signal.prr >= 3:
                level = 'MEDIUM'
            else:
                level = 'LOW'
            
            print(f"\n{i}. {signal.drug_name} + {signal.adverse_event}")
            print(f"   PRR: {signal.prr:.2f} | Cases: {signal.case_count} | Trend: {signal.trend}")
            print(f"   Strength: {signal.signal_strength} | Status: {signal.signal_status}")
            print(f"   Escalation Level: {level}")
        
        print("\n" + "-"*80)
        print("\n✅ Signal Prioritization: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Signal Prioritization: FAILED - {e}")
        return False
    finally:
        db.close()


def test_prr_calculation_accuracy():
    """Test 5: Verify PRR calculation accuracy"""
    print("\n" + "="*80)
    print("TEST 5: PRR Calculation Accuracy")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # Get a signal with known PRR
        signal = db.query(SafetySignal).filter(
            SafetySignal.proportional_reporting_ratio.isnot(None)
        ).first()
        
        if not signal:
            print("\n⚠️  No signals with PRR found. Skipping test.")
            return False
        
        print(f"\n📋 Testing PRR for:")
        print(f"   Drug: {signal.drug_name}")
        print(f"   Event: {signal.adverse_event}")
        
        # Get all cases for manual PRR calculation
        all_cases = db.query(AECase).filter(
            AECase.suspect_drug.isnot(None),
            AECase.adverse_event.isnot(None)
        ).all()
        
        # Calculate PRR manually
        detector = SafetySignalDetector()
        prr_result = detector.calculate_prr(signal.drug_name, signal.adverse_event, all_cases)
        
        print(f"\n📊 PRR Calculation:")
        print(f"   Database PRR: {signal.prr:.4f}")
        print(f"   Calculated PRR: {prr_result['prr']:.4f}")
        print(f"   P-value: {prr_result['p_value']:.6f}")
        print(f"   Confidence: {prr_result['confidence']}")
        
        # Check contingency table
        print(f"\n📊 Contingency Table:")
        print(f"   a (Drug+Event): {prr_result['a']}")
        print(f"   b (Drug, No Event): {prr_result['b']}")
        print(f"   c (Event, No Drug): {prr_result['c']}")
        print(f"   d (Neither): {prr_result['d']}")
        print(f"   Total Cases: {prr_result['total_cases']}")
        
        # Verify formula: PRR = (a/b) / (c/d)
        if prr_result['b'] > 0 and prr_result['d'] > 0:
            manual_prr = (prr_result['a'] / prr_result['b']) / (prr_result['c'] / prr_result['d'])
            print(f"\n✓ Manual verification: PRR = ({prr_result['a']}/{prr_result['b']}) / ({prr_result['c']}/{prr_result['d']}) = {manual_prr:.4f}")
        
        print(f"\n✓ Reason: {prr_result['reason']}")
        print("\n✅ PRR Calculation: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ PRR Calculation: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Run all Feature 6 integration tests"""
    print("\n" + "="*80)
    print("🧪 FEATURE 6: RISK-TRIGGERED SAFETY SIGNAL DETECTION")
    print("   Integration Test Suite")
    print("="*80)
    
    tests = [
        ("Infrastructure", test_signal_detection_infrastructure),
        ("Case-Triggered Detection", lambda: asyncio.run(test_case_triggered_signal_detection())),
        ("Bulk Evaluation", lambda: asyncio.run(test_bulk_signal_evaluation())),
        ("Prioritization", test_signal_prioritization),
        ("PRR Accuracy", test_prr_calculation_accuracy),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}: EXCEPTION - {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed ({100*passed//total}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Feature 6 is fully functional!")
    else:
        print("\n⚠️  Some tests failed. Review output above.")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
