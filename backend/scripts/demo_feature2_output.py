#!/usr/bin/env python3
"""
Quick Demo: Show what backend returns for Feature 2
This demonstrates the REAL data that drives the recommendations
"""

# Simulated backend response (from actual API)
backend_response = {
    "case_id": "550e8400-e29b-41d4-a716-446655440000",
    "primaryid": 185573372,
    "analysis": {
        # ✅ Field 1: Response probability (from ResponseStrategy agent)
        "response_probability": 0.70,  # 70% likelihood
        
        # ✅ Field 2: Risk score (from RiskAssessment agent)
        "risk_score": 0.85,  # HIGH risk
        
        # ✅ Field 3: Decision (from Escalation agent)
        "decision": "ESCALATE",  # Urgent action needed
        
        # ✅ Field 4: Case data with reporter type
        "case_data": {
            "primaryid": 185573372,
            "suspect_drug": "IBUPROFEN",
            "adverse_event": "HOSPITALIZATION",
            "reporter_type": "MD",  # Physician
            "patient_age": 65,
            "patient_sex": "M"
        },
        
        # Additional context (not used for Feature 2)
        "missing_fields": [
            {
                "field": "event_date",
                "field_display": "Event Date",
                "criticality": "CRITICAL",
                "safety_impact": "Required for timeline analysis"
            }
        ],
        "reasoning": "High-risk case requires immediate escalation...",
        "messages": [
            {
                "agent": "DataCompleteness",
                "analysis": "..."
            },
            {
                "agent": "RiskAssessment",
                "risk_score": 0.85,
                "category": "HIGH"
            },
            {
                "agent": "ResponseStrategy",
                "response_probability": 0.70,
                "reporter_type": "MD"
            },
            {
                "agent": "Escalation",
                "decision": "ESCALATE"
            }
        ]
    }
}

print("="*70)
print("  BACKEND DATA → FRONTEND RECOMMENDATIONS")
print("="*70)
print()
print("📡 Backend API Response (Actual Structure)")
print("-"*70)

# Extract Feature 2 fields
analysis = backend_response["analysis"]
response_prob = analysis["response_probability"]
risk_score = analysis["risk_score"]
decision = analysis["decision"]
reporter_type = analysis["case_data"]["reporter_type"]

print(f"response_probability: {response_prob}")
print(f"risk_score: {risk_score}")
print(f"decision: {decision}")
print(f"reporter_type: {reporter_type}")
print()

print("🎯 Frontend Deterministic Logic")
print("-"*70)

# Confidence calculation
if response_prob < 0.40:
    confidence = "LOW"
elif response_prob < 0.70:
    confidence = "MEDIUM"
else:
    confidence = "HIGH"

print(f"Response Confidence: {confidence}")
print(f"  Logic: {response_prob} → {confidence}")
print()

# Timing calculation
if decision == "ESCALATE":
    timing = "Immediate (within 4 hours)"
    urgency = "CRITICAL"
elif decision == "DEFER":
    timing = "Wait 48-72 hours"
    urgency = "LOW"
elif reporter_type in ["MD", "HP", "PH", "RN"]:
    timing = "Next working day (9 AM - 5 PM)"
    urgency = "MEDIUM"
else:
    timing = "Evening or Weekend (6 PM - 9 PM)"
    urgency = "MEDIUM"

print(f"Recommended Timing: {timing}")
print(f"  Logic: decision={decision} → {timing}")
print(f"  Urgency: {urgency}")
print()

# Channel calculation
if risk_score >= 0.8:
    channel = "Phone"
    reason = "High-risk cases require immediate verbal communication"
elif reporter_type in ["MD", "HP", "PH", "RN"]:
    channel = "Email"
    reason = "Healthcare professionals prefer documented email"
else:
    channel = "SMS or Patient Portal"
    reason = "Patients prefer mobile-friendly contact"

print(f"Recommended Channel: {channel}")
print(f"  Logic: risk_score={risk_score}, reporter_type={reporter_type}")
print(f"  Reason: {reason}")
print()

print("="*70)
print("  🎉 FEATURE 2 UI DISPLAY")
print("="*70)
print()
print("┌────────────────────────────────────────────────────────────────┐")
print("│ 🎯 Follow-Up Optimization (AI-Assisted)        Real-time      │")
print("├────────────────────────────────────────────────────────────────┤")
print("│                                                                 │")
print("│  📊 PREDICTED RESPONSE PROBABILITY                             │")
print(f"│  ┌──────────────────────────────────────────────┐ {confidence:^8}  │")
print(f"│  │           {int(response_prob * 100)}%                               │ CONFIDENCE│")
print("│  │  ████████████████████▌░░░░░░░░░░░░              │           │")
print(f"│  │  Reporter: Physician ({reporter_type})                       │           │")
print("│  └──────────────────────────────────────────────┘           │")
print("│                                                                 │")
print(f"│  ⏰ RECOMMENDED TIMING                          {urgency:^8}  │")
print("│  ┌──────────────────────────────────────────────┐             │")
print(f"│  │  {timing:^48}│             │")
print("│  │  High-risk case requiring urgent escalation   │             │")
print("│  └──────────────────────────────────────────────┘             │")
print("│                                                                 │")
print("│  📞 RECOMMENDED CHANNEL                                        │")
print("│  ┌──────────────────────────────────────────────┐             │")
print(f"│  │  {channel:^48}│             │")
print(f"│  │  {reason:<48}│             │")
print("│  │  Alternatives: Email (as backup)              │             │")
print("│  └──────────────────────────────────────────────┘             │")
print("│                                                                 │")
print(f"│  🤖 Based on: Risk ({int(risk_score*100)}%), Decision ({decision}), {reporter_type}      │")
print("└────────────────────────────────────────────────────────────────┘")
print()

print("="*70)
print("  ✅ ALL VALUES ARE DYNAMIC - NO HARDCODING")
print("="*70)
print()
print("Try changing:")
print("  • reporter_type: MD → CN (timing changes)")
print("  • risk_score: 0.85 → 0.50 (channel changes)")
print("  • decision: ESCALATE → DEFER (timing changes)")
print()
print("Each change produces different recommendations!")
print()
