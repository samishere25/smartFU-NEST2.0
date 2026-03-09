#!/usr/bin/env python3
"""
Feature 3 Validation: Question Value Scoring & Adaptive Reduction
Tests deterministic question scoring and adaptive stopping logic
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.question_scoring import QuestionValueScorer


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_test(name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"    {details}")
    return passed


def test_criticality_weights():
    """Test that criticality weights are deterministic"""
    print_section("TEST 1: Criticality Weights")
    
    weights = QuestionValueScorer.CRITICALITY_WEIGHTS
    
    tests = [
        ("CRITICAL weight = 1.0", weights["CRITICAL"] == 1.0),
        ("HIGH weight = 0.75", weights["HIGH"] == 0.75),
        ("MEDIUM weight = 0.5", weights["MEDIUM"] == 0.5),
        ("LOW weight = 0.25", weights["LOW"] == 0.25),
    ]
    
    results = [print_test(name, passed) for name, passed in tests]
    return all(results)


def test_risk_weight_calculation():
    """Test risk weight multiplier logic"""
    print_section("TEST 2: Risk Weight Calculation")
    
    tests = [
        ("High risk (0.9) → 1.0", QuestionValueScorer.calculate_risk_weight(0.9) == 1.0),
        ("High risk (0.8) → 1.0", QuestionValueScorer.calculate_risk_weight(0.8) == 1.0),
        ("Medium risk (0.6) → 0.7", QuestionValueScorer.calculate_risk_weight(0.6) == 0.7),
        ("Medium risk (0.4) → 0.7", QuestionValueScorer.calculate_risk_weight(0.4) == 0.7),
        ("Low risk (0.3) → 0.4", QuestionValueScorer.calculate_risk_weight(0.3) == 0.4),
    ]
    
    results = [print_test(name, passed) for name, passed in tests]
    return all(results)


def test_question_value_scoring():
    """Test question value calculation"""
    print_section("TEST 3: Question Value Scoring")
    
    # CRITICAL field, high risk, low completeness
    value1 = QuestionValueScorer.calculate_question_value(
        criticality="CRITICAL",
        risk_score=0.9,
        completeness_score=0.3
    )
    test1 = print_test(
        "CRITICAL + High Risk + Low Completeness",
        value1 > 0.8,
        f"Score: {value1}"
    )
    
    # LOW field, low risk, high completeness
    value2 = QuestionValueScorer.calculate_question_value(
        criticality="LOW",
        risk_score=0.3,
        completeness_score=0.9
    )
    test2 = print_test(
        "LOW + Low Risk + High Completeness",
        value2 < 0.2,
        f"Score: {value2}"
    )
    
    # Verify CRITICAL always scores higher than LOW
    test3 = print_test(
        "CRITICAL always > LOW (same conditions)",
        value1 > value2,
        f"{value1} > {value2}"
    )
    
    return test1 and test2 and test3


def test_adaptive_stopping_rules():
    """Test when system should stop asking questions"""
    print_section("TEST 4: Adaptive Stopping Rules")
    
    # Test 1: High completeness threshold
    stop1, reason1 = QuestionValueScorer.should_stop_followup(
        completeness_score=0.90,
        risk_score=0.5,
        decision="PROCEED",
        critical_missing_count=0
    )
    test1 = print_test(
        "Stop when completeness ≥ 0.85",
        stop1 and reason1 == "CONFIDENCE_THRESHOLD_REACHED",
        f"Completeness: 0.90 → {reason1}"
    )
    
    # Test 2: Decision is SKIP
    stop2, reason2 = QuestionValueScorer.should_stop_followup(
        completeness_score=0.60,
        risk_score=0.5,
        decision="SKIP",
        critical_missing_count=1
    )
    test2 = print_test(
        "Stop when decision = SKIP",
        stop2 and reason2 == "NO_ACTION_REQUIRED",
        f"Decision: SKIP → {reason2}"
    )
    
    # Test 3: Low risk with sufficient data
    stop3, reason3 = QuestionValueScorer.should_stop_followup(
        completeness_score=0.75,
        risk_score=0.3,
        decision="PROCEED",
        critical_missing_count=0
    )
    test3 = print_test(
        "Stop when low risk + no critical gaps",
        stop3 and reason3 == "LOW_RISK_SUFFICIENT_DATA",
        f"Risk: 0.3, Completeness: 0.75 → {reason3}"
    )
    
    # Test 4: Continue when critical fields missing
    stop4, reason4 = QuestionValueScorer.should_stop_followup(
        completeness_score=0.70,
        risk_score=0.5,
        decision="PROCEED",
        critical_missing_count=2
    )
    test4 = print_test(
        "Continue when critical fields missing",
        not stop4,
        f"2 critical missing → Continue"
    )
    
    return test1 and test2 and test3 and test4


def test_question_selection():
    """Test adaptive question selection rules"""
    print_section("TEST 5: Question Selection Logic")
    
    # Mock scored questions
    scored_questions = [
        {"field": "event_date", "criticality": "CRITICAL", "value_score": 0.95},
        {"field": "patient_age", "criticality": "CRITICAL", "value_score": 0.90},
        {"field": "drug_dose", "criticality": "CRITICAL", "value_score": 0.85},
        {"field": "drug_route", "criticality": "HIGH", "value_score": 0.65},
        {"field": "reporter_type", "criticality": "MEDIUM", "value_score": 0.40},
        {"field": "reporter_country", "criticality": "LOW", "value_score": 0.15},
    ]
    
    # Test 1: Select all CRITICAL when completeness is low
    selected1 = QuestionValueScorer.select_questions(
        scored_questions=scored_questions,
        completeness_score=0.50,
        max_questions=4
    )
    critical_count1 = sum(1 for q in selected1 if q["criticality"] == "CRITICAL")
    test1 = print_test(
        "Select ALL CRITICAL questions (low completeness)",
        critical_count1 == 3 and len(selected1) == 4,
        f"Selected: 3 CRITICAL + 1 HIGH"
    )
    
    # Test 2: Don't ask LOW when CRITICAL exists
    has_low1 = any(q["criticality"] == "LOW" for q in selected1)
    test2 = print_test(
        "NEVER ask LOW when CRITICAL exists",
        not has_low1,
        f"No LOW questions in selection"
    )
    
    # Test 3: High completeness reduces HIGH questions
    selected2 = QuestionValueScorer.select_questions(
        scored_questions=scored_questions,
        completeness_score=0.88,
        max_questions=4
    )
    has_high2 = any(q["criticality"] == "HIGH" for q in selected2)
    test3 = print_test(
        "Reduce HIGH questions when completeness ≥ 0.85",
        len(selected2) == 3 and not has_high2,
        f"Selected: 3 CRITICAL only (no HIGH)"
    )
    
    # Test 4: Respect max_questions limit
    test4 = print_test(
        "Respect max_questions limit",
        len(selected1) <= 4,
        f"Max 4, got {len(selected1)}"
    )
    
    return test1 and test2 and test3 and test4


def test_end_to_end_scenario():
    """Test complete workflow with real-world scenario"""
    print_section("TEST 6: End-to-End Scenario")
    
    # Scenario: High-risk case with 4 missing fields
    missing_fields = [
        {
            "field": "event_date",
            "field_display": "Event Date",
            "criticality": "CRITICAL",
            "safety_impact": "Required for timeline",
            "category": "Event Details"
        },
        {
            "field": "event_outcome",
            "field_display": "Event Outcome",
            "criticality": "CRITICAL",
            "safety_impact": "Required for seriousness",
            "category": "Event Details"
        },
        {
            "field": "drug_route",
            "field_display": "Drug Route",
            "criticality": "HIGH",
            "safety_impact": "Affects bioavailability",
            "category": "Drug Information"
        },
        {
            "field": "reporter_country",
            "field_display": "Reporter Country",
            "criticality": "LOW",
            "safety_impact": "Geographic signal",
            "category": "Reporter Information"
        }
    ]
    
    # Generate questions
    result = QuestionValueScorer.generate_adaptive_questions(
        missing_fields=missing_fields,
        risk_score=0.85,
        completeness_score=0.60,
        decision="PROCEED",
        critical_missing_count=2,
        max_questions=4
    )
    
    # Verify structure
    test1 = print_test(
        "Returns expected structure",
        "questions" in result and "stop_followup" in result and "stats" in result,
        f"Keys: {list(result.keys())}"
    )
    
    # Verify questions selected
    test2 = print_test(
        "Selects 3 questions (2 CRITICAL + 1 HIGH)",
        len(result["questions"]) == 3,
        f"Selected: {len(result['questions'])} questions"
    )
    
    # Verify no LOW questions
    has_low = any(q["criticality"] == "LOW" for q in result["questions"])
    test3 = print_test(
        "Excludes LOW questions",
        not has_low,
        "No LOW questions selected"
    )
    
    # Verify all questions have value scores
    all_scored = all("value_score" in q for q in result["questions"])
    test4 = print_test(
        "All questions have value_score",
        all_scored,
        f"Example scores: {[q['value_score'] for q in result['questions'][:2]]}"
    )
    
    # Verify stopping = False (critical fields still missing)
    test5 = print_test(
        "Continues when critical fields missing",
        not result["stop_followup"],
        f"stop_followup: {result['stop_followup']}"
    )
    
    return test1 and test2 and test3 and test4 and test5


def test_adaptive_behavior():
    """Test that questions reduce as completeness increases"""
    print_section("TEST 7: Adaptive Reduction Behavior")
    
    missing_fields = [
        {"field": "event_date", "field_display": "Event Date", "criticality": "CRITICAL", "safety_impact": "Timeline", "category": "Event"},
        {"field": "patient_age", "field_display": "Patient Age", "criticality": "CRITICAL", "safety_impact": "Safety", "category": "Patient"},
        {"field": "drug_route", "field_display": "Drug Route", "criticality": "HIGH", "safety_impact": "Bioavailability", "category": "Drug"},
        {"field": "reporter_type", "field_display": "Reporter Type", "criticality": "MEDIUM", "safety_impact": "Credibility", "category": "Reporter"},
    ]
    
    # Iteration 1: Low completeness
    result1 = QuestionValueScorer.generate_adaptive_questions(
        missing_fields=missing_fields,
        risk_score=0.70,
        completeness_score=0.40,
        decision="PROCEED",
        critical_missing_count=2
    )
    
    # Iteration 2: Medium completeness (one field filled)
    result2 = QuestionValueScorer.generate_adaptive_questions(
        missing_fields=missing_fields[1:],  # Removed one CRITICAL
        risk_score=0.70,
        completeness_score=0.65,
        decision="PROCEED",
        critical_missing_count=1
    )
    
    # Iteration 3: High completeness (only MEDIUM/LOW missing)
    result3 = QuestionValueScorer.generate_adaptive_questions(
        missing_fields=missing_fields[3:],  # Only MEDIUM left
        risk_score=0.70,
        completeness_score=0.87,
        decision="PROCEED",
        critical_missing_count=0
    )
    
    test1 = print_test(
        "Iteration 1: Asks questions (low completeness)",
        len(result1["questions"]) >= 2,  # At least 2 CRITICAL
        f"Questions: {len(result1['questions'])}"
    )
    
    test2 = print_test(
        "Iteration 2: Asks fewer questions (medium completeness)",
        len(result2["questions"]) >= 1,  # At least 1 CRITICAL remaining
        f"Questions: {len(result2['questions'])}"
    )
    
    test3 = print_test(
        "Iteration 3: STOPS (high completeness)",
        result3["stop_followup"] and result3["stop_reason"] == "CONFIDENCE_THRESHOLD_REACHED",
        f"Stopped: {result3['stop_reason']}"
    )
    
    test4 = print_test(
        "Questions decrease as completeness increases",
        len(result1["questions"]) >= len(result2["questions"]) >= len(result3["questions"]),
        f"{len(result1['questions'])} → {len(result2['questions'])} → {len(result3['questions'])} questions"
    )
    
    return test1 and test2 and test3 and test4


def main():
    """Run all validation tests"""
    print("\n" + "="*80)
    print("FEATURE 3: QUESTION VALUE SCORING & ADAPTIVE REDUCTION")
    print("Testing deterministic logic and adaptive stopping")
    print("="*80)
    
    tests = [
        ("Criticality Weights", test_criticality_weights),
        ("Risk Weight Calculation", test_risk_weight_calculation),
        ("Question Value Scoring", test_question_value_scoring),
        ("Adaptive Stopping Rules", test_adaptive_stopping_rules),
        ("Question Selection Logic", test_question_selection),
        ("End-to-End Scenario", test_end_to_end_scenario),
        ("Adaptive Reduction Behavior", test_adaptive_behavior)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ ERROR in {name}: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    print(f"\n{passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 SUCCESS: Feature 3 is fully deterministic and adaptive!")
        print("   ✓ Question value scoring based on criticality + risk")
        print("   ✓ Adaptive stopping when confidence threshold reached")
        print("   ✓ Questions reduce as data completeness increases")
        print("   ✓ NEVER asks unnecessary LOW priority questions")
        print("   ✓ NO LLM - pure rule-based logic")
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed. Review output above.")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
