"""
Test Connected Orchestration: Feature-1 → Feature-2 → Feature-3
"""
import asyncio
import sys
sys.path.insert(0, '/Users/swapnilchidrawar/Downloads/smartfu/backend')

from app.agents.graph import UnifiedOrchestrator, SmartFUState, CaseContext

async def test_connected_flow():
    """Test the connected orchestration flow"""
    
    # Create test state
    state = SmartFUState(
        case_id='test-123',
        case_data={
            'primaryid': 123,
            'suspect_drug': 'Lisinopril',
            'adverse_event': 'Severe cough and dizziness',
            'reporter_type': 'MD',
            'patient_age': 65,
            'is_serious': True
        },
        missing_fields=[
            {'field_name': 'event_outcome', 'criticality': 'CRITICAL'},
            {'field_name': 'drug_route', 'criticality': 'HIGH'}
        ],
        risk_score=0.0,
        response_probability=0.0,
        decision='PENDING',
        questions=[],
        reasoning='',
        messages=[],
        decision_history=[],
        reporter_history=[],
        case_pattern_memory={},
        agent_confidences={},
        agent_reasonings={}
    )
    
    # Create context
    context = UnifiedOrchestrator.create_context()
    
    print('=' * 60)
    print('CONNECTED ORCHESTRATION TEST')
    print('Feature-1 → Feature-2 → Feature-3 Flow')
    print('=' * 60)
    
    # Run connected flow
    result_state, result_context = await UnifiedOrchestrator.execute_connected_flow(state, context)
    
    print()
    print(f'Execution Order: {result_context["execution_order"]}')
    print(f'Feature Status: {result_context["feature_status"]}')
    print()
    
    print('--- FEATURE-1 OUTPUTS (Risk & Medical) ---')
    risk_out = result_context.get("risk_outputs", {})
    print(f'  Risk Score: {risk_out.get("risk_score", "N/A")}')
    print(f'  Risk Category: {risk_out.get("risk_category", "N/A")}')
    print(f'  Medical Seriousness: {risk_out.get("medical_seriousness_hint", "N/A")}')
    print(f'  Regulatory Urgency: {risk_out.get("regulatory_urgency", "N/A")}')
    print(f'  Confidence: {risk_out.get("confidence_score", "N/A")}')
    print()
    
    print('--- FEATURE-2 OUTPUTS (Strategy & Follow-Up) ---')
    strat_out = result_context.get("strategy_outputs", {})
    print(f'  Decision: {strat_out.get("decision", "N/A")}')
    print(f'  Stop Followup Flag: {strat_out.get("stop_followup_flag", "N/A")}')
    print(f'  Recommended Channel: {strat_out.get("recommended_channel", "N/A")}')
    print(f'  Followup Priority: {strat_out.get("followup_priority", "N/A")}')
    print(f'  Engagement Risk: {strat_out.get("engagement_risk", "N/A")}')
    print()
    
    print('--- FEATURE-3 OUTPUTS (Adaptive Questions) ---')
    questions = result_state.get("questions", [])
    print(f'  Questions Count: {len(questions)}')
    print(f'  Stop Followup: {result_state.get("stop_followup", "N/A")}')
    if questions:
        print(f'  Questions:')
        for q in questions[:3]:
            field = q.get("field", q.get("field_display", "?"))
            crit = q.get("criticality", "?")
            print(f'    - {field} ({crit})')
    print()
    
    print('--- FINAL UNIFIED OUTPUT ---')
    final = UnifiedOrchestrator.build_final_output(result_state, result_context)
    for k, v in final.items():
        if k not in ['optimized_questions', 'question_stats', 'orchestration']:
            print(f'  {k}: {v}')
    print()
    
    # Validation checks
    print('--- VALIDATION CHECKS ---')
    checks_passed = 0
    total_checks = 5
    
    # Check 1: Execution order
    if result_context["execution_order"] == ["Feature-1", "Feature-2", "Feature-3"]:
        print('  ✅ Execution order correct (Feature-1 → Feature-2 → Feature-3)')
        checks_passed += 1
    else:
        print(f'  ❌ Execution order incorrect: {result_context["execution_order"]}')
    
    # Check 2: Feature-1 completed
    if result_context["feature_status"]["Feature-1"] == "COMPLETED":
        print('  ✅ Feature-1 completed')
        checks_passed += 1
    else:
        print(f'  ❌ Feature-1 status: {result_context["feature_status"]["Feature-1"]}')
    
    # Check 3: Feature-2 completed
    if result_context["feature_status"]["Feature-2"] == "COMPLETED":
        print('  ✅ Feature-2 completed')
        checks_passed += 1
    else:
        print(f'  ❌ Feature-2 status: {result_context["feature_status"]["Feature-2"]}')
    
    # Check 4: Feature-3 completed or skipped (based on stop flag)
    f3_status = result_context["feature_status"]["Feature-3"]
    if f3_status in ["COMPLETED", "SKIPPED"]:
        print(f'  ✅ Feature-3 {f3_status.lower()}')
        checks_passed += 1
    else:
        print(f'  ❌ Feature-3 status: {f3_status}')
    
    # Check 5: Final output has all required fields
    required_fields = ['risk_score', 'risk_category', 'recommended_channel', 
                       'followup_priority', 'stop_followup_flag', 'confidence_score']
    missing = [f for f in required_fields if f not in final]
    if not missing:
        print('  ✅ Final output has all required fields')
        checks_passed += 1
    else:
        print(f'  ❌ Missing fields in output: {missing}')
    
    print()
    print('=' * 60)
    if checks_passed == total_checks:
        print(f'✅ ALL {total_checks} VALIDATION CHECKS PASSED')
    else:
        print(f'⚠️ {checks_passed}/{total_checks} checks passed')
    print('=' * 60)


if __name__ == "__main__":
    asyncio.run(test_connected_flow())
