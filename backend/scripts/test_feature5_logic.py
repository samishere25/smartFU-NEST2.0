"""
Test Feature 5: Explainable AI Layer Logic
Tests deterministic explanation generation using ONLY existing analysis data.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.explainability import ExplainabilityBuilder


def test_decision_summary():
    """Test decision summary generation"""
    print("\n" + "="*70)
    print("TEST 1: Decision Summary Generation")
    print("="*70)
    
    # Test case 1: High risk, low completeness, moderate confidence
    analysis1 = {
        "decision": "PROCEED",
        "response_probability": 0.65,
        "risk_score": 0.75,
        "completeness_score": 0.45,
        "case_id": "TEST-001"
    }
    
    summary1 = ExplainabilityBuilder.build_decision_summary(analysis1)
    
    assert summary1["decision"] == "PROCEED", "Decision mismatch"
    assert summary1["decision_label"] == "Immediate Follow-Up Required", "Label mismatch"
    assert summary1["confidence_level"] == "MODERATE", "Confidence level mismatch"
    assert 0.0 <= summary1["confidence_score"] <= 1.0, "Confidence out of range"
    assert "regulatory_compliance" in summary1, "Missing regulatory compliance"
    print("✅ Test 1.1: High risk case - decision summary correct")
    
    # Test case 2: Low risk, high completeness, high confidence
    analysis2 = {
        "decision": "SKIP",
        "response_probability": 0.85,
        "risk_score": 0.25,
        "completeness_score": 0.90,
        "case_id": "TEST-002"
    }
    
    summary2 = ExplainabilityBuilder.build_decision_summary(analysis2)
    
    assert summary2["decision"] == "SKIP", "Decision mismatch"
    assert summary2["decision_label"] == "No Follow-Up Required", "Label mismatch"
    assert summary2["confidence_level"] == "VERY_HIGH", "Confidence level mismatch"
    assert "High confidence" in summary2["primary_reasoning"], "Missing confidence in reasoning"
    print("✅ Test 1.2: Low risk case - decision summary correct")
    
    # Test case 3: Escalation required
    analysis3 = {
        "decision": "ESCALATE",
        "response_probability": 0.25,
        "risk_score": 0.85,
        "completeness_score": 0.35,
        "case_id": "TEST-003"
    }
    
    summary3 = ExplainabilityBuilder.build_decision_summary(analysis3)
    
    assert summary3["decision"] == "ESCALATE", "Decision mismatch"
    assert summary3["decision_label"] == "Human Review Required", "Label mismatch"
    assert summary3["confidence_level"] == "VERY_LOW", f"Confidence level should be VERY_LOW for 0.25"
    print("✅ Test 1.3: Escalation case - decision summary correct")
    
    print("\n✅ Decision Summary: 3/3 tests passed")


def test_contributing_factors():
    """Test contributing factors generation"""
    print("\n" + "="*70)
    print("TEST 2: Contributing Factors Generation")
    print("="*70)
    
    # Test case 1: Critical missing data
    analysis1 = {
        "missing_fields": [
            {"field_name": "suspect_drug", "criticality": "CRITICAL"},
            {"field_name": "adverse_event", "criticality": "CRITICAL"},
            {"field_name": "patient_age", "criticality": "HIGH"}
        ],
        "risk_score": 0.80,
        "completeness_score": 0.40,
        "response_probability": 0.70
    }
    
    factors1 = ExplainabilityBuilder.build_contributing_factors(analysis1)
    
    assert factors1["data_completeness"]["impact_level"] == "CRITICAL", "Data impact should be CRITICAL"
    assert factors1["data_completeness"]["critical_missing"] == 2, "Should detect 2 critical missing"
    assert factors1["risk_severity"]["impact_level"] == "CRITICAL", "Risk impact should be CRITICAL"
    assert factors1["reporter_engagement"]["impact_level"] == "POSITIVE", "Reporter engagement should be POSITIVE"
    assert "overall_weight_distribution" in factors1, "Missing weight distribution"
    print("✅ Test 2.1: Critical missing data - factors correct")
    
    # Test case 2: Low missing data, moderate risk
    analysis2 = {
        "missing_fields": [
            {"field_name": "reporter_country", "criticality": "MEDIUM"}
        ],
        "risk_score": 0.55,
        "completeness_score": 0.85,
        "response_probability": 0.45
    }
    
    factors2 = ExplainabilityBuilder.build_contributing_factors(analysis2)
    
    assert factors2["data_completeness"]["impact_level"] == "LOW", "Data impact should be LOW"
    assert factors2["data_completeness"]["critical_missing"] == 0, "No critical missing"
    assert factors2["risk_severity"]["impact_level"] == "MODERATE", "Risk impact should be MODERATE"
    assert "GVP Module IX" in factors2["risk_severity"]["regulatory_note"], "Missing GVP reference"
    print("✅ Test 2.2: Good completeness case - factors correct")
    
    # Test case 3: High missing, low response probability
    analysis3 = {
        "missing_fields": [
            {"field_name": "f1", "criticality": "HIGH"},
            {"field_name": "f2", "criticality": "HIGH"},
            {"field_name": "f3", "criticality": "MEDIUM"},
            {"field_name": "f4", "criticality": "LOW"}
        ],
        "risk_score": 0.30,
        "completeness_score": 0.60,
        "response_probability": 0.20
    }
    
    factors3 = ExplainabilityBuilder.build_contributing_factors(analysis3)
    
    assert factors3["data_completeness"]["impact_level"] == "HIGH", "Data impact should be HIGH"
    assert factors3["data_completeness"]["high_missing"] == 2, "Should detect 2 high missing"
    assert factors3["reporter_engagement"]["impact_level"] == "LOW", "Reporter impact should be LOW"
    print("✅ Test 2.3: High missing data - factors correct")
    
    print("\n✅ Contributing Factors: 3/3 tests passed")


def test_agent_trace():
    """Test agent trace generation"""
    print("\n" + "="*70)
    print("TEST 3: Agent Trace Generation")
    print("="*70)
    
    # Test case 1: Full agent workflow
    analysis1 = {
        "agent_decisions": [
            {
                "agent": "DataCompleteness",
                "reasoning": "Analyzed data quality",
                "completeness_score": 0.75,
                "missing_count": 3
            },
            {
                "agent": "RiskAssessment",
                "reasoning": "Evaluated safety risk",
                "risk_score": 0.65
            },
            {
                "agent": "ResponseStrategy",
                "reasoning": "Selected follow-up strategy",
                "decision": "PROCEED"
            },
            {
                "agent": "QuestionGeneration",
                "reasoning": "Generated high-value questions",
                "questions_count": 5,
                "stop_followup": False
            }
        ],
        "messages": [],
        "timestamp": "2024-01-15T10:30:00"
    }
    
    trace1 = ExplainabilityBuilder.build_agent_trace(analysis1)
    
    assert trace1["total_steps"] == 4, "Should have 4 trace steps"
    assert trace1["deterministic"] == True, "Should be deterministic"
    assert trace1["llm_free_explanation"], "Should be LLM-free"
    assert len(trace1["trace_steps"]) == 4, "Should have 4 steps"
    
    # Check step structure
    first_step = trace1["trace_steps"][0]
    assert first_step["step_number"] == 1, "Step number mismatch"
    assert first_step["agent_name"] == "DataCompleteness", "Agent name mismatch"
    assert "Data Quality" in first_step["agent_description"], "Missing description"
    assert "regulatory_checkpoint" in first_step, "Missing regulatory checkpoint"
    print("✅ Test 3.1: Full workflow trace - structure correct")
    
    # Test case 2: Adaptive stopping workflow
    analysis2 = {
        "agent_decisions": [
            {
                "agent": "QuestionGeneration",
                "reasoning": "Adaptive stopping triggered",
                "questions_count": 0,
                "stop_followup": True
            },
            {
                "agent": "FollowUpOrchestration",
                "reasoning": "Follow-up not required",
                "followup_required": False
            }
        ]
    }
    
    trace2 = ExplainabilityBuilder.build_agent_trace(analysis2)
    
    assert trace2["total_steps"] == 2, "Should have 2 steps"
    assert "Adaptive stopping" in trace2["trace_steps"][0]["output_summary"], "Missing adaptive stopping"
    print("✅ Test 3.2: Adaptive stopping trace - output correct")
    
    # Test case 3: Escalation workflow
    analysis3 = {
        "agent_decisions": [
            {
                "agent": "EscalationLogic",
                "reasoning": "Human review required",
                "escalated": True
            }
        ]
    }
    
    trace3 = ExplainabilityBuilder.build_agent_trace(analysis3)
    
    assert trace3["total_steps"] == 1, "Should have 1 step"
    assert "Escalation: Yes" in trace3["trace_steps"][0]["output_summary"], "Missing escalation flag"
    print("✅ Test 3.3: Escalation trace - flag correct")
    
    print("\n✅ Agent Trace: 3/3 tests passed")


def test_human_oversight():
    """Test human oversight section generation"""
    print("\n" + "="*70)
    print("TEST 4: Human Oversight Generation")
    print("="*70)
    
    # Test case 1: Mandatory review (escalation)
    analysis1 = {
        "decision": "ESCALATE",
        "response_probability": 0.25,
        "risk_score": 0.85
    }
    
    oversight1 = ExplainabilityBuilder.build_human_oversight(analysis1)
    
    assert oversight1["override_allowed"] == True, "Override should be allowed"
    assert oversight1["override_status"] == "MANDATORY_REVIEW", "Should require mandatory review"
    assert oversight1["requires_mandatory_review"] == True, "Mandatory review flag missing"
    assert "GVP Module V" in oversight1["override_guidance"], "Missing GVP reference"
    assert len(oversight1["audit_requirements"]) >= 5, "Should have extra audit requirement"
    print("✅ Test 4.1: Escalation case - mandatory review required")
    
    # Test case 2: Recommended review (high risk)
    analysis2 = {
        "decision": "PROCEED",
        "response_probability": 0.65,
        "risk_score": 0.70
    }
    
    oversight2 = ExplainabilityBuilder.build_human_oversight(analysis2)
    
    assert oversight2["override_status"] == "RECOMMENDED", "Should recommend review"
    assert oversight2["requires_mandatory_review"] == False, "Should not be mandatory"
    assert len(oversight2["review_checklist"]) >= 5, "Should have review checklist"
    print("✅ Test 4.2: High risk case - review recommended")
    
    # Test case 3: Optional review (low risk)
    analysis3 = {
        "decision": "SKIP",
        "response_probability": 0.90,
        "risk_score": 0.20
    }
    
    oversight3 = ExplainabilityBuilder.build_human_oversight(analysis3)
    
    assert oversight3["override_status"] == "OPTIONAL", "Review should be optional"
    assert oversight3["requires_mandatory_review"] == False, "Should not be mandatory"
    assert "regulatory_compliance" in oversight3, "Missing regulatory compliance"
    assert "gvp_module_v" in oversight3["regulatory_compliance"], "Missing GVP module V"
    print("✅ Test 4.3: Low risk case - optional review")
    
    # Test case 4: Low confidence triggers review
    analysis4 = {
        "decision": "DEFER",
        "response_probability": 0.25,
        "risk_score": 0.45
    }
    
    oversight4 = ExplainabilityBuilder.build_human_oversight(analysis4)
    
    assert oversight4["requires_mandatory_review"] == True, "Low confidence should trigger review"
    print("✅ Test 4.4: Low confidence - triggers review")
    
    print("\n✅ Human Oversight: 4/4 tests passed")


def test_complete_explanation():
    """Test complete explanation generation"""
    print("\n" + "="*70)
    print("TEST 5: Complete Explanation Generation")
    print("="*70)
    
    # Full analysis object
    analysis = {
        "case_id": "TEST-COMPLETE-001",
        "decision": "PROCEED",
        "response_probability": 0.72,
        "risk_score": 0.68,
        "completeness_score": 0.75,
        "missing_fields": [
            {"field_name": "patient_weight", "criticality": "HIGH"},
            {"field_name": "drug_dose", "criticality": "MEDIUM"}
        ],
        "agent_decisions": [
            {
                "agent": "DataCompleteness",
                "reasoning": "Data quality assessed",
                "completeness_score": 0.75,
                "missing_count": 2
            },
            {
                "agent": "RiskAssessment",
                "reasoning": "Risk evaluated",
                "risk_score": 0.68
            },
            {
                "agent": "ResponseStrategy",
                "reasoning": "Follow-up recommended",
                "decision": "PROCEED"
            }
        ],
        "timestamp": "2024-01-15T12:00:00"
    }
    
    complete = ExplainabilityBuilder.build_complete_explanation(analysis)
    
    # Check top-level structure
    assert "explainability_version" in complete, "Missing version"
    assert complete["deterministic"] == True, "Should be deterministic"
    assert complete["llm_free"] == True, "Should be LLM-free"
    assert complete["regulatory_compliant"] == True, "Should be regulatory compliant"
    print("✅ Test 5.1: Top-level structure correct")
    
    # Check all sections present
    assert "decision_summary" in complete, "Missing decision_summary"
    assert "contributing_factors" in complete, "Missing contributing_factors"
    assert "agent_trace" in complete, "Missing agent_trace"
    assert "human_oversight" in complete, "Missing human_oversight"
    print("✅ Test 5.2: All 4 sections present")
    
    # Check decision summary
    decision_summary = complete["decision_summary"]
    assert decision_summary["decision"] == "PROCEED", "Decision mismatch"
    assert decision_summary["confidence_level"] == "HIGH", "Confidence level mismatch"
    assert "regulatory_compliance" in decision_summary, "Missing regulatory compliance"
    print("✅ Test 5.3: Decision summary section valid")
    
    # Check contributing factors
    factors = complete["contributing_factors"]
    assert "data_completeness" in factors, "Missing data completeness"
    assert "risk_severity" in factors, "Missing risk severity"
    assert "reporter_engagement" in factors, "Missing reporter engagement"
    assert "overall_weight_distribution" in factors, "Missing weight distribution"
    print("✅ Test 5.4: Contributing factors section valid")
    
    # Check agent trace
    trace = complete["agent_trace"]
    assert trace["total_steps"] == 3, "Should have 3 steps"
    assert len(trace["trace_steps"]) == 3, "Should have 3 trace steps"
    assert trace["deterministic"] == True, "Trace should be deterministic"
    print("✅ Test 5.5: Agent trace section valid")
    
    # Check human oversight
    oversight = complete["human_oversight"]
    assert oversight["override_allowed"] == True, "Override should be allowed"
    assert "audit_requirements" in oversight, "Missing audit requirements"
    assert "regulatory_compliance" in oversight, "Missing regulatory compliance"
    assert "review_checklist" in oversight, "Missing review checklist"
    print("✅ Test 5.6: Human oversight section valid")
    
    # Check metadata
    metadata = complete["metadata"]
    assert metadata["feature"] == "Feature 5: Explainable AI Layer", "Feature name mismatch"
    assert metadata["llm_generation_used"] == False, "Should not use LLM"
    assert metadata["ai_model_used"] == False, "Should not use AI model"
    assert "GVP" in metadata["regulatory_frameworks"], "Missing GVP framework"
    assert metadata["audit_ready"] == True, "Should be audit ready"
    assert metadata["transparent"] == True, "Should be transparent"
    assert metadata["reproducible"] == True, "Should be reproducible"
    print("✅ Test 5.7: Metadata section valid")
    
    print("\n✅ Complete Explanation: 7/7 tests passed")


def test_deterministic_behavior():
    """Test that explanations are deterministic (same input = same output)"""
    print("\n" + "="*70)
    print("TEST 6: Deterministic Behavior Validation")
    print("="*70)
    
    analysis = {
        "case_id": "TEST-DET-001",
        "decision": "DEFER",
        "response_probability": 0.55,
        "risk_score": 0.50,
        "completeness_score": 0.65,
        "missing_fields": [{"field_name": "test", "criticality": "MEDIUM"}],
        "agent_decisions": [
            {"agent": "DataCompleteness", "reasoning": "Test", "completeness_score": 0.65}
        ]
    }
    
    # Generate explanation twice
    exp1 = ExplainabilityBuilder.build_complete_explanation(analysis)
    exp2 = ExplainabilityBuilder.build_complete_explanation(analysis)
    
    # Check key fields are identical
    assert exp1["decision_summary"]["decision"] == exp2["decision_summary"]["decision"], "Decision changed"
    assert exp1["decision_summary"]["confidence_score"] == exp2["decision_summary"]["confidence_score"], "Confidence changed"
    assert exp1["contributing_factors"]["data_completeness"]["impact_level"] == exp2["contributing_factors"]["data_completeness"]["impact_level"], "Data impact changed"
    assert exp1["agent_trace"]["total_steps"] == exp2["agent_trace"]["total_steps"], "Trace steps changed"
    assert exp1["human_oversight"]["override_status"] == exp2["human_oversight"]["override_status"], "Override status changed"
    
    print("✅ Test 6.1: Same input produces identical explanations")
    print("✅ Test 6.2: No randomness detected")
    
    print("\n✅ Deterministic Behavior: 2/2 tests passed")


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*70)
    print("FEATURE 5: EXPLAINABLE AI LAYER - COMPREHENSIVE TEST SUITE")
    print("="*70)
    print("Testing deterministic explanation generation using ONLY existing analysis data")
    print("NO LLM generation | NO new AI decisions | NO schema changes")
    print("="*70)
    
    try:
        test_decision_summary()
        test_contributing_factors()
        test_agent_trace()
        test_human_oversight()
        test_complete_explanation()
        test_deterministic_behavior()
        
        print("\n" + "="*70)
        print("🎉 SUCCESS: All Feature 5 tests passed!")
        print("="*70)
        print("Total tests: 22/22 passed (100%)")
        print("\nTest Coverage:")
        print("  ✅ Decision summary generation (3 tests)")
        print("  ✅ Contributing factors generation (3 tests)")
        print("  ✅ Agent trace generation (3 tests)")
        print("  ✅ Human oversight generation (4 tests)")
        print("  ✅ Complete explanation generation (7 tests)")
        print("  ✅ Deterministic behavior validation (2 tests)")
        print("\n" + "="*70)
        print("Feature 5 is ready for integration!")
        print("="*70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
