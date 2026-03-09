# Feature 2: 7-Agent AI Pipeline (LangGraph)

---

## Overview
SmartFU uses a **sequential multi-agent pipeline** built on LangGraph (0.0.19) where 7 specialized agents each handle a different pharmacovigilance domain. Each agent reads from and writes to a shared state dictionary (`SmartFUState`), with outputs flowing to the next agent.

---

## 2.1 Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    SmartFUState (TypedDict)                       │
│  40+ fields: case_data, risk_score, medical_reasoning,           │
│  engagement_risk, questions, decision, confidences, history...   │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
   ┌───────────────┐
   │   Agent 1      │  DATA COMPLETENESS
   │   "What's      │  → DataCompletenessService
   │   missing?"    │  → Outputs: missing_fields[], completeness_score
   └───────┬───────┘
           ▼
   ┌───────────────┐
   │   Agent 2      │  MEDICAL REASONING (RAG)
   │   "What does   │  → MedicalReasoningAgent (BioBERT + FAISS)
   │   literature   │  → Outputs: seriousness_hint, critical_fields,
   │   say?"        │    medical_confidence, regulatory_implication
   └───────┬───────┘
           ▼
   ┌───────────────┐
   │   Agent 3      │  RISK ASSESSMENT
   │   "How serious │  → SemanticRiskEngine (SentenceTransformer)
   │   is this?"    │  → Outputs: risk_score, risk_category (H/M/L),
   └───────┬───────┘    risk_confidence, risk_reasoning
           ▼
   ┌───────────────┐
   │   Agent 4      │  RESPONSE STRATEGY
   │   "Will they   │  → predict_response() + adapt_engagement_risk()
   │   respond?"    │  → Outputs: response_probability, engagement_risk,
   └───────┬───────┘    followup_priority, followup_frequency
           ▼
   ┌───────────────┐
   │   Agent 5      │  ESCALATION
   │   "Should we   │  → Mistral LLM reasoning + threshold logic
   │   escalate?"   │  → Outputs: decision (PROCEED/DEFER/SKIP/ESCALATE),
   └───────┬───────┘    escalation_needed, escalation_reason
           ▼
   ┌───────────────┐
   │   Agent 6      │  QUESTION GENERATION
   │   "What should │  → QuestionValueScorer (RL-enhanced)
   │   we ask?"     │  → Outputs: questions[] (scored + ranked),
   └───────┬───────┘    max_questions=4, question texts via Mistral
           ▼
   ┌───────────────┐
   │   Agent 7      │  FOLLOW-UP ORCHESTRATION
   │   "How do we   │  → FollowUpOrchestrator
   │   deliver?"    │  → Outputs: recommended_channel, priority,
   └───────┬───────┘    timing, delivery configuration
           ▼
   ┌───────────────┐
   │   Finalize     │  CONFIDENCE AGGREGATION
   │   Weighted     │  → final_confidence_score (see weights below)
   │   aggregation  │  → critical_followup_fields
   └───────────────┘
```

---

## 2.2 SmartFUState — The Shared State

All agents read from and write to this TypedDict:

```python
class SmartFUState(TypedDict):
    # Core case data
    case_id: str
    case_data: Dict
    missing_fields: List[Dict]
    
    # Decision
    risk_score: float
    response_probability: float
    decision: Literal["PROCEED", "DEFER", "SKIP", "ESCALATE"]
    questions: List[Dict]
    reasoning: str
    messages: List
    
    # Memory (cross-session learning)
    decision_history: List
    reporter_history: List
    case_pattern_memory: Dict
    agent_confidences: Dict
    agent_reasonings: Dict
    
    # Medical RAG (Agent 2 output)
    medical_seriousness_hint: str
    medical_critical_fields: List[str]
    medical_reasoning_text: str
    medical_confidence: float
    medical_regulatory_implication: str
    medical_followup_urgency: str
    
    # Risk Assessment (Agent 3 output)
    risk_category: str          # HIGH/MEDIUM/LOW
    risk_confidence: float
    risk_reasoning: str
    
    # Engagement (Agent 4 output)
    prediction_confidence: float
    engagement_risk: str        # HIGH_RISK/MEDIUM_RISK/LOW_RISK_ENGAGEMENT
    followup_priority: str      # CRITICAL/HIGH/MEDIUM/LOW
    followup_frequency: float   # hours between attempts
    escalation_needed: bool
    escalation_reason: str
    engagement_reasoning: str
    prediction_method: str      # ML_MODEL/FALLBACK
    
    # Feature-3 inputs (for adaptive questioning)
    answered_fields: List[str]
    reviewer_questions: List[Dict]
    days_to_deadline: int
    previous_question_attempts: int
    
    # Final output
    recommended_channel: str    # PHONE/EMAIL/WHATSAPP
    final_confidence_score: float
    critical_followup_fields: List[str]
```

---

## 2.3 Agent Details

### Agent 1: Data Completeness
- **Function**: `data_completeness_agent(state: SmartFUState) -> SmartFUState`
- **Service**: `DataCompletenessService`
- Scans all case fields against ICH E2B requirements
- Produces `MissingField` records with safety_criticality, regulatory_requirement scores
- See Feature 1 doc for full details

### Agent 2: Medical Reasoning (RAG)
- **Function**: `medical_reasoning_agent(state: SmartFUState) -> SmartFUState`
- **Classes**: `RAGRetriever` (Singleton), `MedicalReasoningAgent`, `MedicalSynonymExpander`
- **Embedding Model**: BioBERT (`pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb`)
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (70% rerank + 30% original)
- **Index**: FAISS (`knowledge_base/faiss_index.bin`)
- **Pipeline**: Query expansion → BioBERT embed → FAISS top-10 → cross-encoder rerank → top-5 aggregate
- **Confidence**: `top_score × 0.6 + consensus_factor × 0.4` (capped at 0.98)
- See Feature 1 doc for full RAG pipeline details

### Agent 3: Risk Assessment
- **Function**: `risk_assessment_agent(state: SmartFUState) -> SmartFUState`
- **Class**: `SemanticRiskEngine`
- **Model**: SentenceTransformer `all-MiniLM-L6-v2`
- **Data**: 21 serious event examples + 7 medium event examples
- **Thresholds**: ≥0.6 cosine similarity → HIGH, ≥0.4 → MEDIUM, else LOW
- **Fallback**: Keyword matching if SentenceTransformer unavailable
- See Feature 1 doc for scoring details

### Agent 4: Response Strategy
- **Function**: `response_strategy_agent(state: SmartFUState) -> SmartFUState`
- **Methods**: `predict_response()` (ML model), `adapt_engagement_risk()`
- **ML Model**: Trained on historical response patterns
- **Features**: reporter_type, channel, time_since_report, past_response_rate
- **Output Classifications**:
  - Engagement Risk: `HIGH_RISK_ENGAGEMENT`, `MEDIUM_RISK_ENGAGEMENT`, `LOW_RISK_ENGAGEMENT`
  - Follow-up Priority: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - Follow-up Frequency: hours between attempts (e.g., 24, 48, 72)
- **Prediction Method**: `ML_MODEL` if trained model available, else `FALLBACK` (heuristic)

### Agent 5: Escalation
- **Function**: `escalation_agent(state: SmartFUState) -> SmartFUState`
- Uses Mistral LLM for reasoning generation
- **Decision Matrix**:

| Condition | Decision |
|---|---|
| Risk HIGH + response_prob < 0.3 | `ESCALATE` |
| Risk HIGH + days_to_deadline ≤ 3 | `ESCALATE` |
| Risk MEDIUM + response_prob > 0.5 | `PROCEED` |
| Risk LOW + completeness > 0.8 | `SKIP` |
| Regulatory deadline passed | `ESCALATE` |
| Human override requested | Follow override |

### Agent 6: Question Generation
- **Function**: `question_generation_agent(state: SmartFUState) -> SmartFUState`
- **Service**: `QuestionValueScorer` (1022 lines)
- **Max Questions**: 4 (from AI pipeline alone; other sources add more)
- **See Feature 3 doc** for complete scoring algorithm

### Agent 7: Follow-Up Orchestration
- **Function**: `followup_orchestration_agent(state: SmartFUState) -> SmartFUState`
- **Service**: `FollowUpOrchestrator`
- **Channel Selection Logic**:

| Risk Level | Priority | Channel |
|---|---|---|
| HIGH / CRITICAL | URGENT | PHONE (Twilio Voice) |
| MEDIUM | HIGH | EMAIL or WHATSAPP |
| LOW | NORMAL | EMAIL |

### Finalizer: Confidence Aggregation
- **Function**: `finalize_orchestration_output(state: SmartFUState) -> SmartFUState`
- **Weighted Scoring**:

| Agent | Weight |
|---|---|
| Risk Assessment | 20% (0.20) |
| Medical Reasoning | 20% (0.20) |
| Response Strategy | 25% (0.25) |
| Escalation | 20% (0.20) |
| Question Generation | 10% (0.10) |
| Follow-Up Orchestration | 5% (0.05) |

$$\text{FinalConfidence} = \sum_{i=1}^{6} w_i \times c_i$$

Where $w_i$ = agent weight, $c_i$ = agent confidence score.

---

## 2.4 Connected Flow Architecture (UnifiedOrchestrator)

Beyond the sequential pipeline, SmartFU implements a **Connected Flow** that links the three feature groups:

```
Feature 1 (Risk + Medical)
    │
    ├── risk_outputs: risk_score, risk_category, seriousness
    ├── medical_outputs: critical_fields, urgency, reasoning
    │
    ▼
Feature 2 (Strategy)
    │
    ├── strategy_outputs: response_probability, engagement_risk
    ├── escalation_outputs: decision, escalation_needed
    │
    ▼
Feature 3 (Adaptive Questioning)
    │
    ├── Uses risk from F1 to weight question criticality
    ├── Uses engagement from F2 to adjust question count
    └── Generates final questions with channel recommendation
```

### UnifiedOrchestrator Class
- **File**: `backend/app/agents/graph.py`
- **Constants**:
  - `DAYS_TO_DEADLINE_CRITICAL = 3`
  - `HIGH_RISK_THRESHOLD = 0.7`
  - `LOW_CONFIDENCE_THRESHOLD = 0.3`
- **Methods**: `execute_feature_1()`, `execute_feature_2()`, `execute_feature_3()`, `execute_connected_flow()`, `build_final_output()`
- **Safety Guarantee**: Cannot suppress follow-up for HIGH seriousness cases
- **Fallback**: If connected flow fails → falls back to `smartfu_agent()` (sequential pipeline)

### CaseContext (Inter-Feature Communication)
```python
class CaseContext(TypedDict):
    risk_outputs: Dict[str, Any]         # Feature 1 → Feature 2
    strategy_outputs: Dict[str, Any]     # Feature 2 → Feature 3
    questioning_inputs: Dict[str, Any]   # Feature 3 inputs
    execution_order: List[str]           # Ordered feature execution
    feature_status: Dict[str, str]       # PENDING/COMPLETED/SKIPPED/FAILED
```

---

## 2.5 Standalone Pipeline Runner

```python
async def execute_followup_pipeline(case_id: str) -> Dict:
    """
    Complete standalone pipeline that:
    1. Loads case from DB
    2. Runs 7-agent pipeline
    3. Stores FollowUpDecision record
    4. Returns analysis result
    """
```

Used by: `POST /api/cases/by-primaryid/{id}/analyze` endpoint

---

## 2.6 How to Explain to Judges

> "Our AI is not a single LLM call. It's 7 specialized agents in a pipeline, each handling a different pharmacovigilance domain. The data completeness agent checks what's missing. The medical reasoning agent uses RAG — BioBERT embeddings over a FAISS index of FDA guidelines — to understand the drug-event relationship. The risk assessment agent uses SentenceTransformer to classify seriousness. And so on. Each agent has its own confidence score, and they're aggregated with domain-specific weights to produce a final decision. This gives us explainability, auditability, and reliability that a single LLM call cannot provide."

---

*See F3_QUESTION_GENERATION.md for how Agent 6's questions are merged with 3 other sources and capped at 5.*
