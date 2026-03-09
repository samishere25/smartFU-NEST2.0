# Feature 8: Explainability & Human Governance

---

## Overview
SmartFU's AI is **never autonomous**. Every decision comes with a human-readable explanation, a regulatory checkpoint, and a governance level. High-risk decisions require **mandatory human review**. This feature ensures that the AI is a tool for PV specialists — not a replacement.

---

## 8.1 Architecture

**File**: `backend/app/services/explainability.py` (400 lines)

```
┌──────────────────────────────────────────────────────────┐
│                  ExplainabilityBuilder                     │
│          (All @staticmethod — no LLM dependency)          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────┐  ┌────────────────────────────────┐ │
│  │ Confidence       │  │ Regulatory Checkpoint          │ │
│  │ Level Mapping    │  │ Mapping (Agent → Regulation)   │ │
│  └─────────────────┘  └────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────┐  ┌────────────────────────────────┐ │
│  │ Contributing     │  │ Human Override Logic            │ │
│  │ Factor Weights   │  │ MANDATORY / RECOMMENDED /      │ │
│  │                  │  │ OPTIONAL                        │ │
│  └─────────────────┘  └────────────────────────────────┘ │
│                                                           │
│  KEY DESIGN: No LLM call needed for explanations.        │
│  Entirely rule-based for reliability and speed.           │
└──────────────────────────────────────────────────────────┘
```

### Why No LLM?
Explanations must be **reliable, consistent, and fast**. Using an LLM for explanations introduces:
- Hallucination risk (unacceptable for regulatory context)
- Latency (explanations must be instant)
- Non-determinism (same case should always produce same explanation)

The ExplainabilityBuilder uses **pure Python logic** — @staticmethod methods with no state.

---

## 8.2 Confidence Levels

```python
CONFIDENCE_LEVELS = {
    "very_high": {"min": 0.9, "label": "Very High Confidence", 
                  "recommendation": "Automated processing acceptable"},
    "high":      {"min": 0.7, "label": "High Confidence",
                  "recommendation": "Standard review recommended"},
    "moderate":  {"min": 0.5, "label": "Moderate Confidence",
                  "recommendation": "Detailed review required"},
    "low":       {"min": 0.3, "label": "Low Confidence",
                  "recommendation": "Manual review mandatory"},
    "very_low":  {"min": 0.0, "label": "Very Low Confidence",
                  "recommendation": "Full manual assessment required"}
}
```

| Confidence Score | Level | Review Requirement |
|---|---|---|
| ≥ 0.90 | Very High | Automated processing OK |
| ≥ 0.70 | High | Standard review recommended |
| ≥ 0.50 | Moderate | Detailed review required |
| ≥ 0.30 | Low | **Manual review mandatory** |
| < 0.30 | Very Low | **Full manual assessment required** |

---

## 8.3 Agent → Regulatory Checkpoint Mapping

Each agent in the pipeline maps to a specific regulatory framework:

```python
REGULATORY_CONTEXT = {
    "DataCompleteness": {
        "regulation": "ICH E2B(R3)",
        "section": "Individual Case Safety Report",
        "checkpoint": "Data completeness validation"
    },
    "RiskAssessment": {
        "regulation": "GVP Module IX",
        "section": "Signal Management",
        "checkpoint": "Risk classification and scoring"
    },
    "MedicalReasoning": {
        "regulation": "ICH E2A",
        "section": "Clinical Safety Data Management",
        "checkpoint": "Medical plausibility assessment"
    },
    "ResponseStrategy": {
        "regulation": "EMA GVP Module VI",
        "section": "Management and Reporting",
        "checkpoint": "Reporter engagement assessment"
    },
    "Escalation": {
        "regulation": "ICH E2A Section 3",
        "section": "Expedited Reporting",
        "checkpoint": "Escalation decision"
    },
    "QuestionGeneration": {
        "regulation": "EMA GVP Module VI",
        "section": "Follow-up of Cases",
        "checkpoint": "Question relevance and priority"
    },
    "FollowUpOrchestration": {
        "regulation": "EMA GVP Module I",
        "section": "Quality Management",
        "checkpoint": "Communication channel selection"
    }
}
```

---

## 8.4 Explainability Methods (6)

### `build_decision_explanation(state: SmartFUState) -> Dict`
Produces a comprehensive explanation of the final decision:

```json
{
    "decision": "PROCEED",
    "confidence_level": "High Confidence",
    "confidence_score": 0.76,
    "recommendation": "Standard review recommended",
    "reasoning_summary": "Case involves serious adverse event (hepatotoxicity) 
                          with HIGH risk score (0.78). Medical reasoning suggests
                          plausible drug-event relationship. Reporter is HCP (MD)
                          with high predicted response probability (0.82).",
    "contributing_factors": {
        "data_completeness": {
            "weight": 0.40,
            "score": 0.67,
            "description": "Case is 67% complete, missing 8 fields"
        },
        "risk_assessment": {
            "weight": 0.35,
            "score": 0.78,
            "description": "HIGH risk - hepatotoxicity is a known serious AE"
        },
        "reporter_qualification": {
            "weight": 0.25,
            "score": 0.90,
            "description": "HCP reporter (MD) - reliable medical source"
        }
    },
    "regulatory_checkpoints": [...],
    "human_review_requirement": "RECOMMENDED"
}
```

### `build_agent_explanation(agent_name: str, agent_output: Dict) -> Dict`
Explains individual agent output with regulatory context.

### `calculate_contributing_factors(state: SmartFUState) -> Dict`
Weighted contribution breakdown:

| Factor | Weight | Purpose |
|---|---|---|
| Data Completeness | 40% | How complete is the case? |
| Risk Assessment | 35% | How serious is the event? |
| Reporter Qualification | 25% | How reliable is the source? |

### `map_regulatory_checkpoint(agent_name: str) -> Dict`
Returns the ICH/GVP regulation that applies to each agent's output.

### `determine_human_review_level(state: SmartFUState) -> str`
Returns governance level (see section 8.5).

### `build_audit_explanation(state: SmartFUState) -> Dict`
Produces a structured explanation optimized for audit trail storage.

---

## 8.5 Human Override Logic

### Three Governance Levels

```python
def determine_human_review_level(state):
    decision = state.get("decision", "PROCEED")
    risk_score = state.get("risk_score", 0.0)
    confidence = state.get("final_confidence_score", 0.5)
    
    # MANDATORY — AI cannot proceed without human approval
    if decision == "ESCALATE":
        return "MANDATORY"
    if risk_score >= 0.8:
        return "MANDATORY"
    if confidence < 0.3:
        return "MANDATORY"
    
    # RECOMMENDED — AI can proceed but flags for review
    if risk_score >= 0.5:
        return "RECOMMENDED"
    if confidence < 0.5:
        return "RECOMMENDED"
    
    # OPTIONAL — AI may proceed autonomously
    return "OPTIONAL"
```

### Governance Decision Matrix

| Condition | Level | What Happens |
|---|---|---|
| Decision = ESCALATE | **MANDATORY** | Case queued for Safety Officer review |
| Risk Score ≥ 0.8 | **MANDATORY** | High-risk → must have human sign-off |
| Confidence < 0.3 | **MANDATORY** | AI unsure → human must decide |
| Risk Score ≥ 0.5 | **RECOMMENDED** | Flagged but AI can proceed |
| Confidence < 0.5 | **RECOMMENDED** | Flagged for quality check |
| All else | **OPTIONAL** | AI proceeds, human can review later |

### Override Workflow

```
┌─────────────────────────────────────────────────────┐
│ AI Decision: SKIP (don't follow up)                  │
│ Risk Score: 0.82 (HIGH)                              │
│ Review Level: MANDATORY                              │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ⚠️  MANDATORY HUMAN REVIEW REQUIRED                │
│                                                      │
│  AI recommends: SKIP                                 │
│  Reason: "Low data completeness, reporter unlikely   │
│           to respond based on historical pattern"     │
│                                                      │
│  [ ✅ Accept AI Decision ]                           │
│  [ ✏️  Override → PROCEED ]                          │
│  [ ✏️  Override → ESCALATE ]                         │
│                                                      │
│  Override reason (required): [________________]      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

When a human overrides:
1. Original AI decision logged in audit trail
2. Override decision logged with reason
3. `HUMAN_OVERRIDE` action created in PVAuditTrail
4. Both the AI and human decision are permanently recorded

---

## 8.6 Frontend: Oversight Tab

**File**: `frontend/src/pages/CaseAnalysis.jsx` — Tab 6: "Oversight"

```
┌──────────────────────────────────────────────────────────┐
│                    AI GOVERNANCE                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Decision Explanation                                     │
│  ─────────────────────                                    │
│  "Case involves hepatotoxicity (HIGH risk, score 0.78)    │
│   with HCP reporter (MD). Medical reasoning via BioBERT   │
│   RAG indicates plausible drug-event relationship.         │
│   Recommend PROCEED with 5 follow-up questions via PHONE  │
│   due to 3 days remaining to regulatory deadline."        │
│                                                           │
│  Contributing Factors                                     │
│  ─────────────────────                                    │
│  ┌────────────────────────────────────────────┐           │
│  │ Data Completeness  ▓▓▓▓▓▓▓░░░  67% (40%)  │           │
│  │ Risk Assessment    ▓▓▓▓▓▓▓▓░░  78% (35%)  │           │
│  │ Reporter Quality   ▓▓▓▓▓▓▓▓▓░  90% (25%)  │           │
│  └────────────────────────────────────────────┘           │
│                                                           │
│  Regulatory Checkpoints                                   │
│  ─────────────────────                                    │
│  ✅ ICH E2B(R3) — Data completeness checked               │
│  ✅ GVP Module IX — Risk classified                        │
│  ✅ ICH E2A — Medical plausibility assessed                │
│  ✅ EMA GVP Module VI — Follow-up strategy determined      │
│  ⚠️  ICH E2A §3 — Requires human review (MANDATORY)      │
│                                                           │
│  Human Review: MANDATORY                                  │
│  ─────────────────────                                    │
│  [Accept AI Decision] [Override Decision ▼]               │
│                                                           │
│  Agent Confidence Breakdown                               │
│  ─────────────────────                                    │
│  Risk: 0.85  Medical: 0.72  Response: 0.82                │
│  Escalation: 0.76  Question: 0.91  FollowUp: 0.88        │
│  Final (weighted): 0.82                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 8.7 Explainability in the Pipeline

The ExplainabilityBuilder is called at the **end of every pipeline run**:

```python
# In graph.py — finalize_orchestration_output()
explanation = ExplainabilityBuilder.build_decision_explanation(state)
state["explanation"] = explanation

review_level = ExplainabilityBuilder.determine_human_review_level(state)
state["human_review_level"] = review_level

audit_explanation = ExplainabilityBuilder.build_audit_explanation(state)
# → Stored in PVAuditTrail
```

---

## 8.8 Why This Matters for Regulated Industries

| Without Explainability | With SmartFU Explainability |
|---|---|
| "AI said skip this case" | "AI recommends SKIP because: 67% complete, LOW risk (0.22), routine event (headache), Non-HCP reporter with 85% predicted response rate — data sufficient for non-serious event" |
| Regulator: "Why?" | Regulator: "Show me the audit trail" → complete history with timestamps |
| Cannot override AI | Any decision can be overridden with documented reason |
| Black box | Every agent explains its logic through regulatory checkpoints |
| No accountability | Named actors (AI model version, human user ID, system service) on every action |

---

## 8.9 How to Explain to Judges

> "AI in pharma can't be a black box. When a regulator asks 'why did your system decide not to follow up?', we need a clear answer. SmartFU explains every decision through three lenses: contributing factors (data, risk, reporter), regulatory checkpoints (ICH E2A, GVP Module IX), and governance level. High-risk decisions require mandatory human approval. The AI recommends, the human decides. And everything — the AI recommendation AND the human override — is permanently logged. This isn't AI replacing pharmacovigilance experts; it's AI empowering them."

---

*See DATA_FLOWS.md for complete end-to-end flow diagrams.*
