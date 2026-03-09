"""
SmartFU AI Agent Workflow - Feature-1 + Feature-2 + Feature-3 Orchestration
Context-Aware AI Decision Orchestration with Connected Flow

FEATURES:
Feature-1: Risk & Medical Decision Engine
- Semantic risk reasoning (SentenceTransformer)
- ACTUAL RAG Medical Reasoning (FAISS + FDA/MedDRA/WHO)
- Agent memory support
- Confidence + reasoning outputs
- Updated pipeline order

Feature-2: Strategy & Follow-Up Decision Engine
- ML-based response prediction
- Engagement risk classification (HIGH/MEDIUM/LOW_RISK_ENGAGEMENT)
- Policy-controlled follow-up adaptation
- AI recommends, Policy decides

Feature-3: Adaptive Questioning Engine
- Resume logic, reviewer injection
- Deadline-aware weighting
- Constrained RL optimization

ORCHESTRATION FLOW:
Feature-1 → Feature-2 → Feature-3 (dependency-aware)
"""

from typing import TypedDict, Literal, List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import AIMessage
import numpy as np
import logging

from app.agents.gemini_client import get_gemini_client
from app.core.config import settings

# Initialize client and logger
client = get_gemini_client()
orchestration_logger = logging.getLogger("smartfu.orchestration")


# ============================================================================
# UNIFIED CONTEXT FOR CONNECTED ORCHESTRATION (NEW)
# ============================================================================

class CaseContext(TypedDict):
    """
    Unified context object for passing data between Feature-1, 2, 3.
    Each feature reads from context, not re-calculate upstream logic.
    """
    # Feature-1 outputs (Risk & Medical)
    risk_outputs: Dict[str, Any]
    
    # Feature-2 outputs (Strategy & Follow-Up)  
    strategy_outputs: Dict[str, Any]
    
    # Feature-3 inputs (Adaptive Questioning)
    questioning_inputs: Dict[str, Any]
    
    # Execution tracking
    execution_order: List[str]
    feature_status: Dict[str, str]  # PENDING | COMPLETED | SKIPPED | FAILED


def create_empty_context() -> CaseContext:
    """Create empty unified context"""
    return {
        "risk_outputs": {},
        "strategy_outputs": {},
        "questioning_inputs": {},
        "execution_order": [],
        "feature_status": {
            "Feature-1": "PENDING",
            "Feature-2": "PENDING", 
            "Feature-3": "PENDING"
        }
    }


# ============================================================================
# STEP 3: ENHANCED STATE DEFINITION WITH MEMORY SUPPORT + FEATURE-2
# ============================================================================

class SmartFUState(TypedDict):
    """
    Enhanced GraphState with memory support + Feature-2 engagement risk.
    
    Original fields preserved + new fields for:
    - decision_history: Track all agent decisions
    - reporter_history: Track reporter interactions
    - case_pattern_memory: Store learned patterns
    - Agent confidence scores
    - Agent reasoning texts
    - Feature-2: Engagement risk fields
    """
    # === ORIGINAL FIELDS (unchanged) ===
    case_id: str
    case_data: dict
    missing_fields: list
    risk_score: float
    response_probability: float
    decision: Literal["PROCEED", "DEFER", "SKIP", "ESCALATE"]
    questions: list
    reasoning: str
    messages: list
    
    # === STEP 3: MEMORY FIELDS ===
    decision_history: List[Dict[str, Any]]
    reporter_history: List[Dict[str, Any]]
    case_pattern_memory: Dict[str, Any]
    
    # === STEP 4: CONFIDENCE + REASONING FIELDS ===
    agent_confidences: Dict[str, float]
    agent_reasonings: Dict[str, str]
    
    # === MEDICAL REASONING FIELDS (RAG) ===
    medical_seriousness_hint: str
    medical_critical_fields: List[str]
    medical_reasoning_text: str
    medical_confidence: float
    medical_regulatory_implication: str
    medical_followup_urgency: str
    
    # === FEATURE-3: ADAPTIVE QUESTIONING FIELDS (NEW) ===
    answered_fields: Optional[List[str]]  # Fields already answered (resume logic)
    reviewer_questions: Optional[List[Dict[str, Any]]]  # Reviewer-injected questions
    days_to_deadline: Optional[int]  # Days until regulatory deadline
    previous_question_attempts: Optional[List[str]]  # Previously asked questions
    
    # === RISK ASSESSMENT ENHANCED FIELDS ===
    risk_category: str
    risk_confidence: float
    risk_reasoning: str
    
    # === FEATURE-2: ENGAGEMENT RISK FIELDS (NEW) ===
    prediction_confidence: float
    engagement_risk: str  # HIGH_RISK_ENGAGEMENT | MEDIUM_RISK_ENGAGEMENT | LOW_RISK_ENGAGEMENT
    followup_priority: str  # CRITICAL | HIGH | MEDIUM | LOW
    followup_frequency: int  # hours between attempts
    escalation_needed: bool
    escalation_reason: Optional[str]
    engagement_reasoning: str
    prediction_method: str  # ML_MODEL | FALLBACK
    
    # === FINAL OUTPUT FIELDS (STEP 6) ===
    recommended_channel: str
    final_confidence_score: float
    critical_followup_fields: List[str]


# ============================================================================
# STEP 1: SEMANTIC RISK REASONING ENGINE
# ============================================================================

class SemanticRiskEngine:
    """
    Semantic risk assessment using SentenceTransformer.
    Replaces keyword-based risk logic with semantic similarity.
    """
    
    SERIOUS_EVENT_EXAMPLES = [
        "patient died after taking medication",
        "fatal cardiac arrest",
        "death due to drug reaction",
        "fatal liver failure",
        "sudden death after treatment",
        "anaphylactic shock requiring emergency treatment",
        "cardiac arrest requiring resuscitation",
        "life-threatening allergic reaction",
        "respiratory failure requiring ventilation",
        "severe hypotension requiring vasopressors",
        "hospitalization due to adverse reaction",
        "admitted to ICU",
        "emergency room visit required",
        "prolonged hospital stay",
        "permanent disability from drug",
        "persistent neurological damage",
        "significant incapacity",
        "liver failure",
        "kidney failure requiring dialysis",
        "severe hepatotoxicity",
        "acute renal injury"
    ]
    
    MEDIUM_EVENT_EXAMPLES = [
        "allergic reaction with rash",
        "moderate bleeding event",
        "seizure episode",
        "severe nausea and vomiting",
        "elevated liver enzymes",
        "significant pain",
        "infection requiring antibiotics"
    ]
    
    _model = None
    _serious_embeddings = None
    _medium_embeddings = None
    
    @classmethod
    def _load_model(cls):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ SemanticRiskEngine: Model loaded (all-MiniLM-L6-v2)")
            except ImportError:
                print("⚠️ SemanticRiskEngine: sentence-transformers not available, using fallback")
                cls._model = "FALLBACK"
        return cls._model
    
    @classmethod
    def _compute_embeddings(cls):
        if cls._serious_embeddings is not None:
            return
        
        model = cls._load_model()
        if model == "FALLBACK":
            return
        
        cls._serious_embeddings = model.encode(cls.SERIOUS_EVENT_EXAMPLES, convert_to_numpy=True)
        cls._medium_embeddings = model.encode(cls.MEDIUM_EVENT_EXAMPLES, convert_to_numpy=True)
        print(f"✅ SemanticRiskEngine: Computed embeddings")
    
    @classmethod
    def assess_risk(cls, adverse_event: str, case_data: Optional[Dict] = None) -> Dict[str, Any]:
        if not adverse_event or adverse_event.strip() == "":
            return {
                "risk_score": 0.4,
                "risk_category": "MEDIUM",
                "confidence_score": 0.3,
                "reasoning": "No adverse event description provided. Defaulting to medium risk.",
                "top_similar_events": []
            }
        
        model = cls._load_model()
        
        if model == "FALLBACK":
            return cls._keyword_fallback(adverse_event)
        
        cls._compute_embeddings()
        
        event_embedding = model.encode(adverse_event, convert_to_numpy=True)
        
        # Calculate similarities
        serious_similarities = []
        for i, serious_emb in enumerate(cls._serious_embeddings):
            similarity = float(np.dot(event_embedding, serious_emb) / 
                             (np.linalg.norm(event_embedding) * np.linalg.norm(serious_emb) + 1e-8))
            serious_similarities.append((cls.SERIOUS_EVENT_EXAMPLES[i], similarity))
        
        medium_similarities = []
        for i, medium_emb in enumerate(cls._medium_embeddings):
            similarity = float(np.dot(event_embedding, medium_emb) / 
                             (np.linalg.norm(event_embedding) * np.linalg.norm(medium_emb) + 1e-8))
            medium_similarities.append((cls.MEDIUM_EVENT_EXAMPLES[i], similarity))
        
        max_serious_sim = max(s[1] for s in serious_similarities)
        max_medium_sim = max(s[1] for s in medium_similarities)
        
        top_serious = sorted(serious_similarities, key=lambda x: x[1], reverse=True)[:3]
        
        # Determine risk category and score
        if max_serious_sim >= 0.6:
            risk_score = 0.7 + (max_serious_sim - 0.6) * 0.75
            risk_score = min(1.0, risk_score)
            risk_category = "HIGH"
            confidence = min(0.95, max_serious_sim)
        elif max_serious_sim >= 0.4 or max_medium_sim >= 0.5:
            risk_score = 0.4 + max(max_serious_sim, max_medium_sim) * 0.4
            risk_score = min(0.69, risk_score)
            risk_category = "MEDIUM"
            confidence = min(0.85, max(max_serious_sim, max_medium_sim) + 0.1)
        else:
            risk_score = 0.2 + max(max_serious_sim, max_medium_sim) * 0.3
            risk_score = min(0.39, risk_score)
            risk_category = "LOW"
            confidence = 0.7
        
        reasoning = cls._generate_reasoning(adverse_event, risk_category, risk_score, confidence, top_serious)
        
        return {
            "risk_score": round(risk_score, 3),
            "risk_category": risk_category,
            "confidence_score": round(confidence, 3),
            "reasoning": reasoning,
            "top_similar_events": [{"event": e, "similarity": round(s, 3)} for e, s in top_serious],
            "max_serious_similarity": round(max_serious_sim, 3),
            "max_medium_similarity": round(max_medium_sim, 3)
        }
    
    @classmethod
    def _generate_reasoning(cls, adverse_event: str, category: str, score: float, confidence: float, top_similar: List[tuple]) -> str:
        reasoning_parts = [
            f"Semantic risk analysis classified event as {category} (score: {score:.2f})."
        ]
        
        if top_similar and top_similar[0][1] >= 0.4:
            top_event, top_sim = top_similar[0]
            reasoning_parts.append(f"Highest similarity ({top_sim:.0%}) to: '{top_event[:50]}...'")
        
        if category == "HIGH":
            reasoning_parts.append("Strong semantic similarity to serious adverse events. Expedited reporting may be required.")
        elif category == "MEDIUM":
            reasoning_parts.append("Moderate similarity to known adverse events. Standard monitoring recommended.")
        else:
            reasoning_parts.append("Low similarity to serious events. Routine aggregate reporting appropriate.")
        
        reasoning_parts.append(f"Confidence: {confidence:.0%}.")
        
        return " ".join(reasoning_parts)
    
    @classmethod
    def _keyword_fallback(cls, adverse_event: str) -> Dict[str, Any]:
        event_lower = adverse_event.lower()
        
        serious_keywords = ['death', 'fatal', 'died', 'hospitalization', 'hospital', 
                          'life-threatening', 'disability', 'icu', 'cardiac arrest',
                          'anaphylactic', 'liver failure', 'kidney failure']
        
        medium_keywords = ['serious', 'severe', 'significant', 'bleeding', 'seizure',
                         'allergic', 'infection', 'elevated']
        
        serious_matches = [kw for kw in serious_keywords if kw in event_lower]
        medium_matches = [kw for kw in medium_keywords if kw in event_lower]
        
        if serious_matches:
            risk_score = 0.85
            risk_category = "HIGH"
            confidence = 0.7
            reasoning = f"HIGH risk via keyword matching: {', '.join(serious_matches[:3])}"
        elif medium_matches:
            risk_score = 0.55
            risk_category = "MEDIUM"
            confidence = 0.6
            reasoning = f"MEDIUM risk via keyword matching: {', '.join(medium_matches[:3])}"
        else:
            risk_score = 0.3
            risk_category = "LOW"
            confidence = 0.5
            reasoning = "LOW risk - no serious keywords detected (fallback mode)"
        
        return {
            "risk_score": risk_score,
            "risk_category": risk_category,
            "confidence_score": confidence,
            "reasoning": reasoning + " [Keyword fallback - semantic model unavailable]",
            "top_similar_events": [],
            "fallback_mode": True
        }


# ============================================================================
# AGENT FUNCTIONS
# ============================================================================

async def data_completeness_agent(state: SmartFUState) -> SmartFUState:
    """Analyze data completeness and identify missing critical fields"""
    from app.services.data_completeness import DataCompletenessService
    
    case_data = state["case_data"]
    completeness_result = DataCompletenessService.analyze_case(case_data)
    
    state["missing_fields"] = completeness_result["missing_fields"]
    state["completeness_score"] = completeness_result["completeness_score"]
    state["critical_missing_count"] = completeness_result["critical_missing_count"]
    
    # Initialize memory fields (STEP 3)
    if "decision_history" not in state:
        state["decision_history"] = []
    if "reporter_history" not in state:
        state["reporter_history"] = []
    if "case_pattern_memory" not in state:
        state["case_pattern_memory"] = {}
    if "agent_confidences" not in state:
        state["agent_confidences"] = {}
    if "agent_reasonings" not in state:
        state["agent_reasonings"] = {}
    if 'messages' not in state:
        state["messages"] = []
    
    confidence = min(0.95, completeness_result["completeness_score"] + 0.3)
    reasoning = (
        f"Data Completeness: {completeness_result['fields_present']}/{completeness_result['total_fields_checked']} fields. "
        f"Score: {completeness_result['completeness_score']:.0%}. "
        f"Critical missing: {completeness_result['critical_missing_count']}."
    )
    
    state["agent_confidences"]["DataCompleteness"] = confidence
    state["agent_reasonings"]["DataCompleteness"] = reasoning
    
    state["messages"].append({
        "agent": "DataCompleteness",
        "analysis": reasoning,
        "completeness_score": completeness_result["completeness_score"],
        "missing_count": len(completeness_result["missing_fields"]),
        "confidence": confidence
    })
    
    state["decision_history"].append({
        "agent": "DataCompleteness",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": f"completeness_{completeness_result['completeness_score']:.0%}",
        "confidence": confidence,
        "reasoning": reasoning[:200]
    })
    
    return state


async def medical_reasoning_agent(state: SmartFUState) -> SmartFUState:
    """
    STEP 2: Medical Reasoning Agent (ACTUAL RAG)
    
    Uses FAISS vector store with:
    - FDA Drug Labels
    - MedDRA Terminology  
    - WHO Guidelines
    """
    from app.agents.medical_reasoning_agent import MedicalReasoningAgent
    
    case_data = state.get("case_data", {})
    adverse_event = case_data.get("adverse_event", "")
    
    result = MedicalReasoningAgent.analyze(adverse_event, case_data)
    
    state["medical_seriousness_hint"] = result["medical_seriousness_hint"]
    state["medical_critical_fields"] = result["critical_followup_fields"]
    state["medical_reasoning_text"] = result["reasoning_text"]
    state["medical_confidence"] = result["confidence_score"]
    state["medical_regulatory_implication"] = result.get("regulatory_implication", "Standard monitoring")
    state["medical_followup_urgency"] = result.get("followup_urgency", "ROUTINE")
    
    state["agent_confidences"]["MedicalReasoning"] = result["confidence_score"]
    state["agent_reasonings"]["MedicalReasoning"] = result["reasoning_text"]
    
    state["messages"].append({
        "agent": "MedicalReasoning",
        "seriousness_hint": result["medical_seriousness_hint"],
        "confidence": result["confidence_score"],
        "reasoning": result["reasoning_text"],
        "matched_categories": result.get("matched_categories", []),
        "retrieval_method": result.get("retrieval_method", "UNKNOWN"),
        "knowledge_sources": result.get("knowledge_sources", [])
    })
    
    state["decision_history"].append({
        "agent": "MedicalReasoning",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": result["medical_seriousness_hint"],
        "confidence": result["confidence_score"],
        "reasoning": result["reasoning_text"][:200],
        "retrieval_method": result.get("retrieval_method", "UNKNOWN")
    })
    
    return state


async def risk_assessment_agent(state: SmartFUState) -> SmartFUState:
    """STEP 1: Semantic Risk Assessment Agent"""
    case_data = state["case_data"]
    completeness_score = state.get("completeness_score", 0.5)
    critical_missing = state.get("critical_missing_count", 0)
    
    adverse_event = case_data.get('adverse_event', '')
    
    risk_result = SemanticRiskEngine.assess_risk(adverse_event, case_data)
    
    risk_score = risk_result["risk_score"]
    risk_category = risk_result["risk_category"]
    risk_confidence = risk_result["confidence_score"]
    
    medical_hint = state.get("medical_seriousness_hint", "MEDIUM")
    if medical_hint == "HIGH" and risk_category != "HIGH":
        risk_score = min(1.0, risk_score + 0.15)
        if risk_score >= 0.7:
            risk_category = "HIGH"
    
    if critical_missing > 0:
        risk_confidence = max(0.3, risk_confidence - (critical_missing * 0.1))
    
    risk_score = max(0.0, min(1.0, risk_score))
    
    reasoning = (
        f"{risk_result['reasoning']} "
        f"Medical RAG hint: {medical_hint}. "
        f"Completeness: {completeness_score:.0%} ({critical_missing} critical missing)."
    )
    
    state["risk_score"] = risk_score
    state["risk_category"] = risk_category
    state["risk_confidence"] = risk_confidence
    state["risk_reasoning"] = reasoning
    
    state["agent_confidences"]["RiskAssessment"] = risk_confidence
    state["agent_reasonings"]["RiskAssessment"] = reasoning
    
    state["messages"].append({
        "agent": "RiskAssessment",
        "risk_score": risk_score,
        "category": risk_category,
        "confidence": risk_confidence,
        "reasoning": reasoning,
        "semantic_analysis": risk_result.get("top_similar_events", [])
    })
    
    state["decision_history"].append({
        "agent": "RiskAssessment",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": f"{risk_category}_{risk_score:.2f}",
        "confidence": risk_confidence,
        "reasoning": reasoning[:200]
    })
    
    return state


# ============================================================================
# FEATURE-2: UPGRADED RESPONSE STRATEGY AGENT
# ============================================================================

async def response_strategy_agent(state: SmartFUState) -> SmartFUState:
    """
    FEATURE-2 UPGRADED: Engagement Risk Adaptation
    
    Pipeline:
    1. Predict response probability (ML model or fallback)
    2. Get prediction confidence
    3. Classify engagement risk
    4. Apply policy-controlled adaptation
    
    AI RECOMMENDS - POLICY DECIDES
    """
    from app.services.engagement_risk_adaptation import adapt_engagement_risk
    from app.services.response_prediction import predict_response
    
    case_data = state["case_data"]
    reporter_type = case_data.get('reporter_type', 'UNKNOWN')
    
    case_data_for_prediction = {**case_data}
    case_data_for_prediction['risk_score'] = state.get('risk_score', 0.5)
    
    prediction_result = predict_response(case_data_for_prediction)
    
    response_probability = prediction_result["response_probability"]
    prediction_confidence = prediction_result["prediction_confidence"]
    prediction_method = prediction_result["prediction_method"]
    
    case_seriousness = state.get("medical_seriousness_hint", "MEDIUM")
    case_risk_score = state.get("risk_score", 0.5)
    
    reporter_history = state.get("reporter_history", [])
    number_of_attempts = len([h for h in reporter_history if h.get("reporter_type") == reporter_type])
    
    time_since_last = None
    if reporter_history:
        last_attempt = reporter_history[-1]
        if "timestamp" in last_attempt:
            try:
                last_time = datetime.fromisoformat(last_attempt["timestamp"])
                time_since_last = (datetime.utcnow() - last_time).total_seconds() / 3600
            except:
                pass
    
    engagement_result = adapt_engagement_risk(
        response_probability=response_probability,
        prediction_confidence=prediction_confidence,
        case_seriousness=case_seriousness,
        case_risk_score=case_risk_score,
        number_of_attempts=number_of_attempts,
        time_since_last_attempt_hours=time_since_last
    )
    
    state["response_probability"] = response_probability
    state["prediction_confidence"] = prediction_confidence
    state["prediction_method"] = prediction_method
    state["engagement_risk"] = engagement_result["engagement_risk"]
    state["followup_priority"] = engagement_result["followup_priority"]
    state["followup_frequency"] = engagement_result["followup_frequency"]
    state["escalation_needed"] = engagement_result["escalation_needed"]
    state["escalation_reason"] = engagement_result.get("escalation_reason")
    state["engagement_reasoning"] = engagement_result["classification_reasoning"]
    
    reasoning = (
        f"Response prob: {response_probability:.0%} ({prediction_method}), "
        f"Confidence: {prediction_confidence:.0%}. "
        f"Engagement: {engagement_result['engagement_risk']}. "
        f"Priority: {engagement_result['followup_priority']}, Frequency: {engagement_result['followup_frequency']}h."
    )
    
    if engagement_result["escalation_needed"]:
        reasoning += f" ESCALATION: {engagement_result['escalation_reason']}"
    
    state["agent_confidences"]["ResponseStrategy"] = prediction_confidence
    state["agent_reasonings"]["ResponseStrategy"] = reasoning
    
    state["messages"].append({
        "agent": "ResponseStrategy",
        "response_probability": response_probability,
        "prediction_confidence": prediction_confidence,
        "prediction_method": prediction_method,
        "engagement_risk": engagement_result["engagement_risk"],
        "followup_priority": engagement_result["followup_priority"],
        "followup_frequency": engagement_result["followup_frequency"],
        "escalation_needed": engagement_result["escalation_needed"],
        "reporter_type": reporter_type,
        "confidence": prediction_confidence,
        "reasoning": reasoning
    })
    
    state["decision_history"].append({
        "agent": "ResponseStrategy",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": engagement_result["engagement_risk"],
        "confidence": prediction_confidence,
        "reasoning": reasoning[:200]
    })
    
    state["reporter_history"].append({
        "reporter_type": reporter_type,
        "predicted_response_rate": response_probability,
        "engagement_risk": engagement_result["engagement_risk"],
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return state


# ============================================================================
# FEATURE-2: UPGRADED ESCALATION AGENT
# ============================================================================

async def escalation_agent(state: SmartFUState) -> SmartFUState:
    """Make final follow-up decision with Feature-2 engagement risk integration"""
    risk_score = state.get("risk_score", 0.0)
    response_prob = state.get("response_probability", 0.0)
    missing_count = len(state.get("missing_fields", []))
    medical_hint = state.get("medical_seriousness_hint", "MEDIUM")
    medical_urgency = state.get("medical_followup_urgency", "ROUTINE")
    
    # Feature-2 inputs
    engagement_risk = state.get("engagement_risk", "MEDIUM_RISK_ENGAGEMENT")
    followup_priority = state.get("followup_priority", "MEDIUM")
    escalation_needed = state.get("escalation_needed", False)
    escalation_reason = state.get("escalation_reason")
    
    if escalation_needed:
        decision = "ESCALATE"
        reasoning_prompt = f"Feature-2 escalation: {escalation_reason}"
        confidence = 0.90
    elif risk_score >= 0.7 and missing_count >= 2:
        decision = "PROCEED"
        reasoning_prompt = "high risk case with critical missing data"
        confidence = 0.85
    elif risk_score >= 0.7 or medical_hint == "HIGH" or medical_urgency == "IMMEDIATE":
        decision = "ESCALATE"
        reasoning_prompt = "high risk/urgency requiring immediate review"
        confidence = 0.90
    elif followup_priority == "CRITICAL":
        decision = "ESCALATE"
        reasoning_prompt = f"Feature-2 critical priority: {engagement_risk}"
        confidence = 0.88
    elif engagement_risk == "LOW_RISK_ENGAGEMENT" and missing_count == 0:
        decision = "SKIP"
        reasoning_prompt = "low engagement risk, case complete"
        confidence = 0.95
    elif response_prob < 0.3 and engagement_risk == "HIGH_RISK_ENGAGEMENT":
        decision = "PROCEED"
        reasoning_prompt = "low response expected but high engagement risk"
        confidence = 0.70
    elif response_prob < 0.3:
        decision = "SKIP"
        reasoning_prompt = "low response probability"
        confidence = 0.75
    elif missing_count == 0:
        decision = "SKIP"
        reasoning_prompt = "case already complete"
        confidence = 0.95
    elif missing_count <= 2 and response_prob >= 0.5:
        decision = "PROCEED"
        reasoning_prompt = "moderate missing data with good response likelihood"
        confidence = 0.80
    else:
        decision = "DEFER"
        reasoning_prompt = "case needs review"
        confidence = 0.65
    
    prompt = f"""Pharmacovigilance follow-up decision explanation:
Decision: {decision}
Risk Score: {risk_score:.2f}
Medical Seriousness (RAG): {medical_hint}
Medical Urgency: {medical_urgency}
Response Probability: {response_prob:.0%}
Engagement Risk (Feature-2): {engagement_risk}
Follow-up Priority (Feature-2): {followup_priority}
Missing Fields: {missing_count}
Context: {reasoning_prompt}

Brief professional explanation (2-3 sentences):"""

    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        ai_reasoning = response.choices[0].message.content
    except Exception as e:
        ai_reasoning = f"{decision}: {reasoning_prompt}. Risk: {risk_score:.2f}, Engagement: {engagement_risk}."
    
    state["decision"] = decision
    state["reasoning"] = ai_reasoning
    
    state["agent_confidences"]["Escalation"] = confidence
    state["agent_reasonings"]["Escalation"] = ai_reasoning
    
    state["messages"].append({
        "agent": "Escalation",
        "decision": decision,
        "confidence": confidence,
        "reasoning": ai_reasoning,
        "engagement_risk": engagement_risk,
        "followup_priority": followup_priority
    })
    
    state["decision_history"].append({
        "agent": "Escalation",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": decision,
        "confidence": confidence,
        "reasoning": ai_reasoning[:200]
    })
    
    return state


async def question_generation_agent(state: SmartFUState) -> SmartFUState:
    """
    Generate adaptive questions with value scoring
    
    Feature-3 Enhanced: Now supports resume logic, reviewer injection,
    deadline weighting, duplicate protection, and RL learning
    """
    from app.services.question_scoring import QuestionValueScorer
    
    missing_fields = state.get("missing_fields", [])
    risk_score = state.get("risk_score", 0.0)
    completeness_score = state.get("completeness_score", 0.0)
    decision = state.get("decision", "PROCEED")
    critical_missing = state.get("critical_missing_count", 0)
    
    # Feature-3: Extract new optional parameters from state
    answered_fields = state.get("answered_fields", None)
    reviewer_questions = state.get("reviewer_questions", None)
    days_to_deadline = state.get("days_to_deadline", None)
    previous_attempts = state.get("previous_question_attempts", None)
    
    # Use enhanced method (falls back to heuristic-only if Feature-3 disabled)
    result = QuestionValueScorer.generate_adaptive_questions_enhanced(
        missing_fields=missing_fields,
        risk_score=risk_score,
        completeness_score=completeness_score,
        decision=decision,
        critical_missing_count=critical_missing,
        max_questions=4,
        # Feature-3 parameters (optional)
        answered_fields=answered_fields,
        reviewer_questions=reviewer_questions,
        days_to_deadline=days_to_deadline,
        previous_attempts=previous_attempts
    )
    
    state["questions"] = result["questions"]
    state["stop_followup"] = result["stop_followup"]
    state["stop_reason"] = result["stop_reason"]
    state["question_stats"] = result["stats"]
    
    confidence = 0.85 if result["questions"] else 0.90
    reasoning = f"Generated {len(result['questions'])} questions. Stop: {result['stop_followup']}."
    
    # Feature-3: Add RL info to reasoning if enabled
    if result["stats"].get("rl_enabled", False):
        reasoning += f" RL-enhanced scoring active."
    
    state["agent_confidences"]["QuestionGeneration"] = confidence
    state["agent_reasonings"]["QuestionGeneration"] = reasoning
    
    state["messages"].append({
        "agent": "QuestionGeneration",
        "questions_count": len(result["questions"]),
        "stop_followup": result["stop_followup"],
        "confidence": confidence,
        "reasoning": reasoning
    })
    
    state["decision_history"].append({
        "agent": "QuestionGeneration",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": f"questions_{len(result['questions'])}",
        "confidence": confidence,
        "reasoning": reasoning
    })
    
    return state


async def followup_orchestration_agent(state: SmartFUState) -> SmartFUState:
    """Follow-Up Orchestration Agent with Feature-2 integration"""
    from app.services.followup_orchestration import FollowUpOrchestrator
    
    questions = state.get("questions", [])
    stop_followup = state.get("stop_followup", False)
    completeness_score = state.get("completeness_score", 0.0)
    risk_score = state.get("risk_score", 0.0)
    decision = state.get("decision", "")
    
    case_data = state.get("case_data", {})
    reporter_type = case_data.get("reporter_type", "OT")
    primaryid = case_data.get("primaryid", 0)
    case_id = state.get("case_id", "")
    
    followup_result = FollowUpOrchestrator.orchestrate_followup(
        case_id=case_id,
        questions=questions,
        stop_followup=stop_followup,
        completeness_score=completeness_score,
        risk_score=risk_score,
        decision=decision,
        reporter_type=reporter_type,
        primaryid=primaryid
    )
    
    engagement_priority = state.get("followup_priority", "MEDIUM")
    engagement_frequency = state.get("followup_frequency", 48)
    
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    orchestrator_priority = followup_result.get("priority", "MEDIUM")
    
    if priority_order.get(engagement_priority, 2) < priority_order.get(orchestrator_priority, 2):
        followup_result["priority"] = engagement_priority
    
    if engagement_frequency:
        followup_result["timing_hours"] = engagement_frequency
    
    state["followup_required"] = followup_result["followup_required"]
    state["followup_created"] = followup_result["followup_created"]
    state["followup_status"] = followup_result["status"]
    state["followup_channel"] = followup_result["channel"]
    state["followup_timing_hours"] = followup_result.get("timing_hours")
    state["followup_priority"] = followup_result.get("priority", "MEDIUM")
    state["followup_details"] = followup_result
    state["recommended_channel"] = followup_result["channel"] or "EMAIL"
    
    confidence = 0.85 if followup_result["followup_required"] else 0.90
    reasoning = f"Channel: {followup_result['channel']}, Priority: {followup_result.get('priority')}, Questions: {followup_result['questions_count']}"
    
    state["agent_confidences"]["FollowUpOrchestration"] = confidence
    state["agent_reasonings"]["FollowUpOrchestration"] = reasoning
    
    state["messages"].append(AIMessage(content=reasoning))
    
    state["decision_history"].append({
        "agent": "FollowUpOrchestration",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": f"channel_{followup_result['channel']}",
        "confidence": confidence,
        "reasoning": reasoning
    })
    
    return state


def finalize_orchestration_output(state: SmartFUState) -> SmartFUState:
    """STEP 6: Finalize orchestration output (updated for Feature-2)"""
    medical_critical = state.get("medical_critical_fields", [])
    missing_fields = [f["field"] for f in state.get("missing_fields", []) if isinstance(f, dict) and "field" in f]
    
    all_critical = list(set(medical_critical + missing_fields))[:8]
    state["critical_followup_fields"] = all_critical
    
    confidences = state.get("agent_confidences", {})
    if confidences:
        weights = {
            "RiskAssessment": 0.20,
            "MedicalReasoning": 0.20,
            "ResponseStrategy": 0.25,
            "Escalation": 0.20,
            "QuestionGeneration": 0.10,
            "FollowUpOrchestration": 0.05
        }
        
        weighted_sum = sum(
            confidences.get(agent, 0.5) * weight 
            for agent, weight in weights.items()
        )
        state["final_confidence_score"] = round(weighted_sum, 3)
    else:
        state["final_confidence_score"] = 0.5
    
    agent_reasonings = state.get("agent_reasonings", {})
    if agent_reasonings:
        key_reasonings = [
            f"[{agent}] {reasoning[:80]}..."
            for agent, reasoning in agent_reasonings.items()
            if agent in ["RiskAssessment", "MedicalReasoning", "ResponseStrategy", "Escalation"]
        ]
        state["reasoning_text"] = " | ".join(key_reasonings)
    
    return state


async def smartfu_agent(state: SmartFUState) -> SmartFUState:
    """Sequential agent workflow"""
    state = await data_completeness_agent(state)
    state = await medical_reasoning_agent(state)
    state = await risk_assessment_agent(state)
    state = await response_strategy_agent(state)
    state = await escalation_agent(state)
    state = await question_generation_agent(state)
    state = await followup_orchestration_agent(state)
    state = finalize_orchestration_output(state)
    return state


GraphState = SmartFUState


async def execute_followup_pipeline(case_id: int) -> dict:
    """Execute full orchestration pipeline on a case"""
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.models import AECase
    from app.agents.medical_reasoning_agent import MedicalReasoningAgent
    from app.agents.risk_assessment_agent import RiskAssessmentAgent
    from app.services.response_prediction import predict_response
    from app.services.engagement_risk_adaptation import adapt_engagement_risk
    import uuid
    
    risk_agent = RiskAssessmentAgent(model_dir="models")
    db = SessionLocal()
    
    try:
        if isinstance(case_id, int):
            case = db.query(AECase).filter(AECase.primaryid == case_id).first()
        else:
            if isinstance(case_id, str):
                case_id = uuid.UUID(case_id)
            case = db.query(AECase).filter(AECase.case_id == case_id).first()
        
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        case_data = {
            "case_id": case.case_id,
            "primaryid": case.primaryid,
            "adverse_event": case.adverse_event or "",
            "drug_name": case.suspect_drug or "",
            "suspect_drug": case.suspect_drug or "",
            "route": case.drug_route or "",
            "occp_cod": case.reporter_type or "",
            "reporter_type": case.reporter_type or "UNKNOWN",
            "age": case.patient_age,
            "patient_age": case.patient_age,
            "sex": case.patient_sex,
            "event_date": str(case.event_date) if case.event_date else None,
            "outcome": case.event_outcome or "",
        }
        
        medical_result = MedicalReasoningAgent.analyze(case_data["adverse_event"], case_data)
        risk_result = await risk_agent.assess(case_data)
        
        case_data['risk_score'] = risk_result["risk_score"]
        response_result = predict_response(case_data)
        
        engagement_result = adapt_engagement_risk(
            response_probability=response_result["response_probability"],
            prediction_confidence=response_result["prediction_confidence"],
            case_seriousness=medical_result.get("medical_seriousness_hint", "MEDIUM"),
            case_risk_score=risk_result["risk_score"],
            number_of_attempts=0
        )
        
        medical_seriousness = medical_result.get("medical_seriousness_hint", "MEDIUM")
        if medical_seriousness == "HIGH":
            risk_result["risk_score"] = max(risk_result["risk_score"], 0.75)
            risk_result["risk_category"] = "HIGH"
        elif medical_seriousness == "LOW" and risk_result["risk_category"] == "HIGH":
            risk_result["risk_score"] = min(risk_result["risk_score"], 0.65)
            risk_result["risk_category"] = "MEDIUM"
        
        final_confidence = 0.5 * risk_result.get("confidence_score", 0.5) + 0.3 * medical_result.get("confidence_score", 0.5) + 0.2 * response_result.get("prediction_confidence", 0.5)
        
        return {
            "risk_score": risk_result["risk_score"],
            "risk_category": risk_result["risk_category"],
            "risk_confidence": risk_result["confidence_score"],
            "risk_reasoning": risk_result["reasoning_text"],
            "medical_seriousness_hint": medical_result["medical_seriousness_hint"],
            "medical_reasoning_text": medical_result["reasoning_text"],
            "medical_confidence": medical_result["confidence_score"],
            "critical_followup_fields": medical_result["critical_followup_fields"],
            "medical_regulatory_implication": medical_result.get("regulatory_implication", ""),
            "medical_followup_urgency": medical_result.get("followup_urgency", "ROUTINE"),
            "response_probability": response_result["response_probability"],
            "prediction_confidence": response_result["prediction_confidence"],
            "prediction_method": response_result["prediction_method"],
            "engagement_risk": engagement_result["engagement_risk"],
            "followup_priority": engagement_result["followup_priority"],
            "followup_frequency": engagement_result["followup_frequency"],
            "escalation_needed": engagement_result["escalation_needed"],
            "escalation_reason": engagement_result.get("escalation_reason"),
            "confidence_score": final_confidence,
            "recommended_channel": _determine_channel(risk_result, medical_result, engagement_result),
            "priority": engagement_result["followup_priority"],
            "case_id": case_id,
            "primaryid": case.primaryid,
            "decision_history": [
                {"agent": "MedicalReasoning", "decision": medical_result["medical_seriousness_hint"], "confidence": medical_result["confidence_score"]},
                {"agent": "RiskAssessment", "decision": risk_result["risk_category"], "confidence": risk_result["confidence_score"]},
                {"agent": "ResponseStrategy", "decision": engagement_result["engagement_risk"], "confidence": response_result["prediction_confidence"]}
            ],
            "reporter_history": [],
            "case_pattern_memory": {}
        }
    finally:
        db.close()


def _determine_channel(risk_result: dict, medical_result: dict, engagement_result: dict = None) -> str:
    risk_cat = risk_result.get("risk_category", "MEDIUM")
    urgency = medical_result.get("followup_urgency", "ROUTINE")
    
    if engagement_result:
        priority = engagement_result.get("followup_priority", "MEDIUM")
        if priority == "CRITICAL":
            return "PHONE"
    
    if risk_cat == "HIGH" or urgency == "IMMEDIATE":
        return "PHONE"
    elif risk_cat == "MEDIUM" or urgency == "HIGH":
        return "EMAIL"
    else:
        return "SMS"


def _determine_priority(risk_result: dict, medical_result: dict) -> str:
    risk_cat = risk_result.get("risk_category", "MEDIUM")
    urgency = medical_result.get("followup_urgency", "ROUTINE")
    
    if risk_cat == "HIGH" or urgency == "IMMEDIATE":
        return "URGENT"
    elif risk_cat == "MEDIUM":
        return "HIGH"
    else:
        return "NORMAL"


# ============================================================================
# UNIFIED ORCHESTRATION: Feature-1 → Feature-2 → Feature-3 Connected Flow
# ============================================================================

class UnifiedOrchestrator:
    """
    Connected Flow Orchestrator for Feature-1 → Feature-2 → Feature-3
    
    RULES:
    - Feature-1 executes first (Risk & Medical Engine)
    - Feature-2 consumes Feature-1 output (Strategy Engine)
    - Feature-3 executes only if stop_followup_flag == False
    - Each feature reads from context, not re-calculate upstream
    - Fallback to sequential execution on failure
    """
    
    # Safety thresholds
    DAYS_TO_DEADLINE_CRITICAL = 3
    HIGH_RISK_THRESHOLD = 0.7
    LOW_CONFIDENCE_THRESHOLD = 0.3
    
    @classmethod
    def create_context(cls) -> CaseContext:
        """Initialize unified context"""
        return create_empty_context()
    
    @classmethod
    async def execute_feature_1(
        cls,
        state: SmartFUState,
        context: CaseContext
    ) -> tuple:
        """
        FEATURE-1: Risk & Medical Decision Engine
        
        Returns:
        - risk_score
        - risk_category
        - medical_seriousness_hint
        - regulatory_urgency
        - confidence_score
        """
        try:
            # Execute Feature-1 agents
            state = await data_completeness_agent(state)
            state = await medical_reasoning_agent(state)
            state = await risk_assessment_agent(state)
            
            # Extract Feature-1 outputs
            risk_outputs = {
                "risk_score": state.get("risk_score", 0.5),
                "risk_category": state.get("risk_category", "MEDIUM"),
                "risk_confidence": state.get("risk_confidence", 0.5),
                "risk_reasoning": state.get("risk_reasoning", ""),
                "medical_seriousness_hint": state.get("medical_seriousness_hint", "MEDIUM"),
                "medical_critical_fields": state.get("medical_critical_fields", []),
                "medical_reasoning_text": state.get("medical_reasoning_text", ""),
                "medical_confidence": state.get("medical_confidence", 0.5),
                "medical_regulatory_implication": state.get("medical_regulatory_implication", ""),
                "medical_followup_urgency": state.get("medical_followup_urgency", "ROUTINE"),
                "confidence_score": state.get("agent_confidences", {}).get("RiskAssessment", 0.5),
                "completeness_score": state.get("completeness_score", 0.0),
                "missing_fields": state.get("missing_fields", [])
            }
            
            # Determine regulatory urgency based on medical analysis
            if risk_outputs["medical_followup_urgency"] == "IMMEDIATE":
                risk_outputs["regulatory_urgency"] = "URGENT"
            elif risk_outputs["risk_category"] == "HIGH":
                risk_outputs["regulatory_urgency"] = "HIGH"
            else:
                risk_outputs["regulatory_urgency"] = "ROUTINE"
            
            # Update context
            context["risk_outputs"] = risk_outputs
            context["execution_order"].append("Feature-1")
            context["feature_status"]["Feature-1"] = "COMPLETED"
            
            orchestration_logger.info(
                f"Feature-1 COMPLETED: risk={risk_outputs['risk_score']:.2f}, "
                f"category={risk_outputs['risk_category']}, "
                f"seriousness={risk_outputs['medical_seriousness_hint']}"
            )
            
            return state, context
            
        except Exception as e:
            orchestration_logger.error(f"Feature-1 FAILED: {e}")
            context["feature_status"]["Feature-1"] = "FAILED"
            
            # Fallback defaults
            context["risk_outputs"] = {
                "risk_score": 0.5,
                "risk_category": "MEDIUM",
                "medical_seriousness_hint": "MEDIUM",
                "regulatory_urgency": "ROUTINE",
                "confidence_score": 0.3
            }
            
            return state, context
    
    @classmethod
    async def execute_feature_2(
        cls,
        state: SmartFUState,
        context: CaseContext
    ) -> tuple:
        """
        FEATURE-2: Strategy & Follow-Up Decision Engine
        
        MUST consume Feature-1 output:
        - risk_category
        - regulatory_urgency
        - confidence_score
        - reporter_type
        - days_to_deadline
        
        Returns:
        - recommended_channel
        - followup_priority
        - stop_followup_flag
        """
        # VALIDATION: Feature-1 must be completed
        if context["feature_status"]["Feature-1"] != "COMPLETED":
            orchestration_logger.warning("Feature-2 called before Feature-1 completion")
        
        try:
            risk_outputs = context.get("risk_outputs", {})
            
            # Inject Feature-1 context into state for Feature-2
            state["risk_score"] = risk_outputs.get("risk_score", state.get("risk_score", 0.5))
            state["risk_category"] = risk_outputs.get("risk_category", state.get("risk_category", "MEDIUM"))
            state["medical_seriousness_hint"] = risk_outputs.get("medical_seriousness_hint", "MEDIUM")
            
            # Execute Feature-2 agents
            state = await response_strategy_agent(state)
            state = await escalation_agent(state)
            
            # Extract Feature-2 outputs
            strategy_outputs = {
                "response_probability": state.get("response_probability", 0.5),
                "prediction_confidence": state.get("prediction_confidence", 0.5),
                "prediction_method": state.get("prediction_method", "FALLBACK"),
                "engagement_risk": state.get("engagement_risk", "MEDIUM_RISK_ENGAGEMENT"),
                "followup_priority": state.get("followup_priority", "MEDIUM"),
                "followup_frequency": state.get("followup_frequency", 48),
                "escalation_needed": state.get("escalation_needed", False),
                "escalation_reason": state.get("escalation_reason"),
                "decision": state.get("decision", "PROCEED"),
                "reasoning": state.get("reasoning", "")
            }
            
            # Determine stop_followup_flag based on decision
            stop_decisions = ["SKIP"]
            strategy_outputs["stop_followup_flag"] = state.get("decision") in stop_decisions
            
            # SAFETY GUARANTEE: Cannot stop follow-up if medical_seriousness == HIGH
            if risk_outputs.get("medical_seriousness_hint") == "HIGH":
                if strategy_outputs["stop_followup_flag"]:
                    orchestration_logger.warning(
                        "SAFETY OVERRIDE: Cannot stop follow-up for HIGH seriousness case"
                    )
                    strategy_outputs["stop_followup_flag"] = False
                    state["decision"] = "PROCEED"
            
            # SAFETY GUARANTEE: Cannot stop if confidence too low
            if risk_outputs.get("confidence_score", 1.0) < cls.LOW_CONFIDENCE_THRESHOLD:
                if strategy_outputs["stop_followup_flag"]:
                    orchestration_logger.warning(
                        "SAFETY OVERRIDE: Cannot stop follow-up with low confidence"
                    )
                    strategy_outputs["stop_followup_flag"] = False
                    state["decision"] = "DEFER"
            
            # Determine recommended channel
            strategy_outputs["recommended_channel"] = cls._determine_channel_from_context(
                risk_outputs, strategy_outputs
            )
            
            # Update context
            context["strategy_outputs"] = strategy_outputs
            context["execution_order"].append("Feature-2")
            context["feature_status"]["Feature-2"] = "COMPLETED"
            
            orchestration_logger.info(
                f"Feature-2 COMPLETED: decision={strategy_outputs['decision']}, "
                f"stop_flag={strategy_outputs['stop_followup_flag']}, "
                f"priority={strategy_outputs['followup_priority']}"
            )
            
            return state, context
            
        except Exception as e:
            orchestration_logger.error(f"Feature-2 FAILED: {e}")
            context["feature_status"]["Feature-2"] = "FAILED"
            
            # Fallback: Continue with follow-up
            context["strategy_outputs"] = {
                "stop_followup_flag": False,
                "followup_priority": "MEDIUM",
                "recommended_channel": "EMAIL",
                "decision": "PROCEED"
            }
            
            return state, context
    
    @classmethod
    async def execute_feature_3(
        cls,
        state: SmartFUState,
        context: CaseContext
    ) -> tuple:
        """
        FEATURE-3: Adaptive Questioning Engine
        
        MUST consume Feature-1 and Feature-2 outputs:
        - risk_category (from Feature-1)
        - regulatory_urgency (from Feature-1)
        - followup_priority (from Feature-2)
        - days_to_deadline
        - previous_attempts
        - reviewer_overrides
        
        MUST NOT independently re-evaluate risk.
        MUST NOT independently decide channel.
        """
        # VALIDATION: Feature-1 and Feature-2 must be completed
        if context["feature_status"]["Feature-1"] != "COMPLETED":
            orchestration_logger.error("Feature-3 BLOCKED: Feature-1 not completed")
            context["feature_status"]["Feature-3"] = "BLOCKED"
            return state, context
        
        if context["feature_status"]["Feature-2"] != "COMPLETED":
            orchestration_logger.error("Feature-3 BLOCKED: Feature-2 not completed")
            context["feature_status"]["Feature-3"] = "BLOCKED"
            return state, context
        
        # CHECK stop_followup_flag from Feature-2
        strategy_outputs = context.get("strategy_outputs", {})
        if strategy_outputs.get("stop_followup_flag", False):
            orchestration_logger.info("Feature-3 SKIPPED: stop_followup_flag=True")
            context["feature_status"]["Feature-3"] = "SKIPPED"
            state["questions"] = []
            state["stop_followup"] = True
            state["stop_reason"] = strategy_outputs.get("decision", "STOP")
            return state, context
        
        try:
            risk_outputs = context.get("risk_outputs", {})
            
            # Build questioning inputs from Feature-1 and Feature-2 context
            questioning_inputs = {
                "risk_category": risk_outputs.get("risk_category", "MEDIUM"),
                "regulatory_urgency": risk_outputs.get("regulatory_urgency", "ROUTINE"),
                "followup_priority": strategy_outputs.get("followup_priority", "MEDIUM"),
                "days_to_deadline": state.get("days_to_deadline"),
                "previous_attempts": state.get("previous_question_attempts", []),
                "reviewer_overrides": state.get("reviewer_questions", []),
                "answered_fields": state.get("answered_fields", [])
            }
            
            context["questioning_inputs"] = questioning_inputs
            
            # SAFETY GUARANTEE: If risk_category == HIGH → critical questions mandatory
            if risk_outputs.get("risk_category") == "HIGH":
                state["_force_critical_questions"] = True
            
            # SAFETY GUARANTEE: If followup_priority == LOW → reduce question volume
            if strategy_outputs.get("followup_priority") == "LOW":
                state["_reduce_question_volume"] = True
            
            # SAFETY GUARANTEE: If days_to_deadline < threshold → prioritize regulatory
            days = state.get("days_to_deadline")
            if days is not None and days < cls.DAYS_TO_DEADLINE_CRITICAL:
                state["_prioritize_regulatory_fields"] = True
            
            # Execute Feature-3 agent
            state = await question_generation_agent(state)
            state = await followup_orchestration_agent(state)
            
            # Update context
            context["execution_order"].append("Feature-3")
            context["feature_status"]["Feature-3"] = "COMPLETED"
            
            orchestration_logger.info(
                f"Feature-3 COMPLETED: questions={len(state.get('questions', []))}, "
                f"stop={state.get('stop_followup', False)}"
            )
            
            return state, context
            
        except Exception as e:
            orchestration_logger.error(f"Feature-3 FAILED: {e}")
            context["feature_status"]["Feature-3"] = "FAILED"
            
            # Fallback: Use missing_fields as basic questions
            state["questions"] = state.get("missing_fields", [])[:4]
            state["stop_followup"] = False
            
            return state, context
    
    @classmethod
    def _determine_channel_from_context(
        cls,
        risk_outputs: dict,
        strategy_outputs: dict
    ) -> str:
        """Determine channel from unified context"""
        priority = strategy_outputs.get("followup_priority", "MEDIUM")
        risk_cat = risk_outputs.get("risk_category", "MEDIUM")
        urgency = risk_outputs.get("regulatory_urgency", "ROUTINE")
        
        if priority == "CRITICAL":
            return "PHONE"
        if risk_cat == "HIGH" or urgency == "URGENT":
            return "PHONE"
        elif risk_cat == "MEDIUM" or urgency == "HIGH":
            return "EMAIL"
        else:
            return "SMS"
    
    @classmethod
    async def execute_connected_flow(
        cls,
        state: SmartFUState,
        context: CaseContext = None
    ) -> tuple:
        """
        Main orchestration: Feature-1 → Feature-2 → Feature-3
        
        Validates execution order and ensures proper data flow.
        Falls back to sequential execution on failure.
        """
        if context is None:
            context = cls.create_context()
        
        orchestration_logger.info("Starting Connected Flow Orchestration")
        
        try:
            # STEP 1: Feature-1 (Risk & Medical)
            state, context = await cls.execute_feature_1(state, context)
            
            # STEP 2: Feature-2 (Strategy) - consumes Feature-1
            state, context = await cls.execute_feature_2(state, context)
            
            # STEP 3: Feature-3 (Questions) - only if follow-up continues
            state, context = await cls.execute_feature_3(state, context)
            
            # Finalize output
            state = finalize_orchestration_output(state)
            
            # Add context to final output
            state["orchestration_context"] = {
                "execution_order": context["execution_order"],
                "feature_status": context["feature_status"],
                "connected_flow": True
            }
            
            orchestration_logger.info(
                f"Connected Flow COMPLETED: {context['execution_order']}"
            )
            
            return state, context
            
        except Exception as e:
            orchestration_logger.error(f"Connected Flow FAILED: {e}. Falling back to sequential.")
            
            # FALLBACK: Use original sequential execution
            state = await smartfu_agent(state)
            context["feature_status"] = {
                "Feature-1": "FALLBACK",
                "Feature-2": "FALLBACK",
                "Feature-3": "FALLBACK"
            }
            state["orchestration_context"] = {
                "execution_order": ["FALLBACK"],
                "feature_status": context["feature_status"],
                "connected_flow": False,
                "fallback_reason": str(e)
            }
            
            return state, context
    
    @classmethod
    def build_final_output(
        cls,
        state: SmartFUState,
        context: CaseContext
    ) -> dict:
        """
        Build final system output from unified context.
        
        OUTPUT STRUCTURE:
        {
            risk_score,
            risk_category,
            recommended_channel,
            followup_priority,
            stop_followup_flag,
            optimized_questions,
            confidence_score
        }
        """
        risk_outputs = context.get("risk_outputs", {})
        strategy_outputs = context.get("strategy_outputs", {})
        
        return {
            # Feature-1 outputs
            "risk_score": risk_outputs.get("risk_score", state.get("risk_score", 0.5)),
            "risk_category": risk_outputs.get("risk_category", state.get("risk_category", "MEDIUM")),
            "medical_seriousness_hint": risk_outputs.get("medical_seriousness_hint", "MEDIUM"),
            "regulatory_urgency": risk_outputs.get("regulatory_urgency", "ROUTINE"),
            
            # Feature-2 outputs
            "recommended_channel": strategy_outputs.get("recommended_channel", state.get("recommended_channel", "EMAIL")),
            "followup_priority": strategy_outputs.get("followup_priority", state.get("followup_priority", "MEDIUM")),
            "stop_followup_flag": strategy_outputs.get("stop_followup_flag", state.get("stop_followup", False)),
            "decision": strategy_outputs.get("decision", state.get("decision", "PROCEED")),
            
            # Feature-3 outputs
            "optimized_questions": state.get("questions", []),
            "question_stats": state.get("question_stats", {}),
            
            # Confidence
            "confidence_score": state.get("final_confidence_score", 0.5),
            
            # Orchestration metadata
            "orchestration": state.get("orchestration_context", {})
        }


# Create wrapper function for backward compatibility
async def smartfu_agent_connected(state: SmartFUState) -> SmartFUState:
    """
    Connected flow orchestration wrapper.
    Use this instead of smartfu_agent for connected Feature-1→2→3 flow.
    """
    context = UnifiedOrchestrator.create_context()
    state, context = await UnifiedOrchestrator.execute_connected_flow(state, context)
    return state


print("✅ SmartFU AI Agents initialized (Feature-1: RAG + Feature-2: Engagement Risk + Feature-3: Adaptive Questions + Connected Orchestration)")