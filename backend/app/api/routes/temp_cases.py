# Just the analyze endpoint fix - will append to existing file

@router.post("/{case_id}/analyze")
async def analyze_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger AI analysis for a case"""
    
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Trigger AI agent workflow
    from app.agents.graph import smartfu_agent, SmartFUState
    
    initial_state = SmartFUState(
        case_id=str(case_id),
        case_data={
            "suspect_drug": case.suspect_drug,
            "adverse_event": case.adverse_event,
            "patient_age": case.patient_age,
            "patient_sex": case.patient_sex,
            "drug_route": case.drug_route,
            "drug_dose": case.drug_dose,
            "event_date": case.event_date,
            "reporter_type": case.reporter_type,
        },
        missing_fields=[],
        risk_score=0.0,
        response_probability=0.0,
        decision="DEFER",
        questions=[],
        reasoning="",
        messages=[]
    )
    
    # Call the agent function directly (not .ainvoke)
    result = await smartfu_agent(initial_state)
    
    return {
        "case_id": str(case_id),
        "analysis": {
            "risk_score": result["risk_score"],
            "risk_category": "HIGH" if result["risk_score"] >= 0.7 else "MEDIUM" if result["risk_score"] >= 0.4 else "LOW",
            "response_probability": result["response_probability"],
            "decision": result["decision"],
            "reasoning": result["reasoning"],
            "missing_fields": result["missing_fields"],
            "agent_messages": result["messages"]
        }
    }
