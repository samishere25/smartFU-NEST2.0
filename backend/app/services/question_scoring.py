"""
Question Value Scoring & Adaptive Reduction Service
Deterministic question prioritization and adaptive stopping logic
NO LLM - pure rule-based scoring

Feature-3 Enhancements:
- Resume Logic
- Reviewer Question Injection  
- Deadline-Aware Dynamic Weighting
- Duplicate Question Protection
- Constrained Reinforcement Learning
"""

from typing import Dict, List, Any, Tuple, Optional
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class QuestionValueScorer:
    """
    Scores questions based on criticality, safety impact, and risk
    Implements adaptive stopping rules

    ALL question text is generated dynamically by Mistral AI.
    No static/predefined question templates.
    """

    # Criticality weights (deterministic)
    CRITICALITY_WEIGHTS = {
        "CRITICAL": 1.0,
        "HIGH": 0.75,
        "MEDIUM": 0.5,
        "LOW": 0.25
    }

    # Feature-3: Regulatory-critical fields (deadline-aware)
    REGULATORY_CRITICAL_FIELDS = {
        "event_date", "event_outcome", "adverse_event",
        "suspect_drug", "patient_age", "patient_sex"
    }

    # Feature-3: RL state file path
    RL_STATE_FILE = "models/question_rl_state.json"

    # Feature-3: RL configuration
    RL_ENABLED = True  # Can be disabled for fallback
    RL_REWARD_WEIGHT = 0.2
    RL_CONSTRAINT_WEIGHT = 0.5
    RL_DUPLICATE_WEIGHT = 0.3

    # Cache for LLM-generated questions (per-session, avoids repeated calls)
    _llm_question_cache: Dict[str, str] = {}

    @classmethod
    def resolve_question_text(
        cls,
        field_name: str,
        field_display: str = "",
        case_context: Optional[Dict] = None,
    ) -> str:
        """
        Generate question text for a missing field using Mistral AI.

        ALL questions are dynamically generated — no static templates.

        Args:
            field_name: The missing field name.
            field_display: Human-readable field name (fallback).
            case_context: Optional known case data for LLM context.

        Returns:
            Question text string (AI-generated).
        """
        # Check cache first
        if field_name in cls._llm_question_cache:
            return cls._llm_question_cache[field_name]

        # Generate via Mistral AI
        try:
            from app.services.cioms_question_generator import generate_cioms_questions
            llm_result = generate_cioms_questions(
                missing_fields=[field_name],
                case_context=case_context,
            )
            if field_name in llm_result:
                cls._llm_question_cache[field_name] = llm_result[field_name]
                return llm_result[field_name]
        except Exception as e:
            logger.warning(f"Mistral question generation failed for {field_name}: {e}")

        # No generic fallback — if Mistral fails, skip this question
        return None

    @classmethod
    def calculate_risk_weight(cls, risk_score: float) -> float:
        """
        Calculate risk weight for question scoring

        Args:
            risk_score: Overall case risk (0.0 to 1.0)

        Returns:
            Risk weight multiplier
        """
        if risk_score >= 0.8:
            return 1.0  # High risk - all questions important
        elif risk_score >= 0.4:
            return 0.7  # Medium risk - prioritize critical
        else:
            return 0.4  # Low risk - only essential questions
    
    @classmethod
    def calculate_question_value(
        cls,
        criticality: str,
        risk_score: float,
        completeness_score: float = 0.0
    ) -> float:
        """
        Calculate deterministic question value score
        
        Formula: criticality_weight × risk_weight × urgency_factor
        
        Args:
            criticality: CRITICAL/HIGH/MEDIUM/LOW
            risk_score: Case risk (0.0 to 1.0)
            completeness_score: Current completeness (0.0 to 1.0)
            
        Returns:
            Question value score (0.0 to 1.0)
        """
        # Base weight from criticality
        criticality_weight = cls.CRITICALITY_WEIGHTS.get(criticality, 0.25)
        
        # Risk-based multiplier
        risk_weight = cls.calculate_risk_weight(risk_score)
        
        # Urgency factor (lower completeness = higher urgency)
        urgency_factor = 1.0 - (completeness_score * 0.3)  # Max 30% reduction
        
        # Calculate final value
        value_score = criticality_weight * risk_weight * urgency_factor
        
        return round(value_score, 3)
    
    @classmethod
    def score_and_rank_questions(
        cls,
        missing_fields: List[Dict[str, Any]],
        risk_score: float,
        completeness_score: float
    ) -> List[Dict[str, Any]]:
        """
        Score all missing fields and rank by value
        
        Args:
            missing_fields: List from DataCompletenessService
            risk_score: Case risk score
            completeness_score: Current completeness
            
        Returns:
            Sorted list of questions with value scores
        """
        scored_questions = []
        
        for field in missing_fields:
            field_name = field["field"]
            criticality = field["criticality"]
            
            # Calculate value score
            value_score = cls.calculate_question_value(
                criticality=criticality,
                risk_score=risk_score,
                completeness_score=completeness_score
            )
            
            # Get question text (LLM for CIOMS fields, None if Mistral fails)
            question_text = cls.resolve_question_text(
                field_name=field_name,
                field_display=field["field_display"],
            )

            # Skip questions where Mistral failed (no generic fallback)
            if question_text is None:
                continue

            scored_questions.append({
                "field": field_name,
                "field_display": field["field_display"],
                "question": question_text,
                "criticality": criticality,
                "safety_impact": field.get("safety_impact", ""),
                "value_score": value_score,
                "category": field.get("category", "Unknown")
            })

        # Sort by value score (descending)
        scored_questions.sort(key=lambda x: x["value_score"], reverse=True)

        return scored_questions
    
    @classmethod
    def should_stop_followup(
        cls,
        completeness_score: float,
        risk_score: float,
        decision: str,
        critical_missing_count: int
    ) -> Tuple[bool, str]:
        """
        Determine if follow-up should stop (adaptive stopping)
        
        Args:
            completeness_score: Current data completeness (0.0 to 1.0)
            risk_score: Case risk (0.0 to 1.0)
            decision: Agent decision (ESCALATE/PROCEED/DEFER/SKIP)
            critical_missing_count: Number of critical fields missing
            
        Returns:
            (should_stop: bool, reason: str)
        """
        # Rule 1: High confidence threshold reached
        # BUT: Never stop if critical fields are still missing - those MUST be collected
        if completeness_score >= 0.85 and critical_missing_count == 0:
            return True, "CONFIDENCE_THRESHOLD_REACHED"
        
        # Rule 2: Decision is to skip follow-up (only if no critical gaps)
        if decision == "SKIP" and critical_missing_count == 0:
            return True, "NO_ACTION_REQUIRED"
        
        # Rule 3: Low risk with sufficient data
        if risk_score < 0.4 and completeness_score >= 0.70 and critical_missing_count == 0:
            return True, "LOW_RISK_SUFFICIENT_DATA"
        
        # Rule 4: Medium risk with no critical fields missing
        if risk_score < 0.7 and completeness_score >= 0.75 and critical_missing_count == 0:
            return True, "SUFFICIENT_DATA_NO_CRITICAL_GAPS"
        
        # Continue follow-up
        return False, None
    
    @classmethod
    def select_questions(
        cls,
        scored_questions: List[Dict[str, Any]],
        completeness_score: float,
        max_questions: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Select which questions to ask based on adaptive rules
        
        Rules:
        - ALWAYS ask ALL CRITICAL questions
        - Ask HIGH questions only if completeness < 0.85
        - NEVER ask LOW questions if CRITICAL exists
        - Limit to max_questions per iteration
        
        Args:
            scored_questions: All scored questions (sorted)
            completeness_score: Current completeness
            max_questions: Max questions per iteration
            
        Returns:
            Selected questions to ask
        """
        selected = []
        
        # Separate by criticality
        critical_questions = [q for q in scored_questions if q["criticality"] == "CRITICAL"]
        high_questions = [q for q in scored_questions if q["criticality"] == "HIGH"]
        medium_questions = [q for q in scored_questions if q["criticality"] == "MEDIUM"]
        low_questions = [q for q in scored_questions if q["criticality"] == "LOW"]
        
        # Rule 1: Always include ALL CRITICAL questions
        selected.extend(critical_questions)
        
        # Rule 2: Add HIGH questions if completeness is low
        if completeness_score < 0.85 and len(selected) < max_questions:
            remaining_slots = max_questions - len(selected)
            selected.extend(high_questions[:remaining_slots])
        
        # Rule 3: Add MEDIUM questions only if no CRITICAL and space available
        if len(critical_questions) == 0 and len(selected) < max_questions:
            remaining_slots = max_questions - len(selected)
            selected.extend(medium_questions[:remaining_slots])
        
        # Rule 4: NEVER add LOW questions if CRITICAL questions exist
        if len(critical_questions) == 0 and len(high_questions) == 0 and len(selected) < max_questions:
            remaining_slots = max_questions - len(selected)
            selected.extend(low_questions[:remaining_slots])
        
        # Enforce max limit
        return selected[:max_questions]
    
    @classmethod
    def generate_adaptive_questions(
        cls,
        missing_fields: List[Dict[str, Any]],
        risk_score: float,
        completeness_score: float,
        decision: str,
        critical_missing_count: int,
        max_questions: int = 4
    ) -> Dict[str, Any]:
        """
        Main entry point: Generate adaptive questions with stopping logic
        
        Args:
            missing_fields: Missing fields from DataCompletenessService
            risk_score: Case risk score
            completeness_score: Current completeness
            decision: Agent decision
            critical_missing_count: Count of critical missing fields
            max_questions: Max questions per iteration
            
        Returns:
            {
                "questions": [...],
                "stop_followup": bool,
                "stop_reason": str or None,
                "stats": {...}
            }
        """
        # GUARD: If no missing fields, no follow-up needed
        if not missing_fields:
            return {
                "questions": [],
                "stop_followup": True,
                "stop_reason": "all_fields_complete",
                "stats": {
                    "completeness_score": completeness_score,
                    "risk_score": risk_score,
                    "critical_missing": 0,
                    "total_missing": 0
                }
            }

        # Check if we should stop
        should_stop, stop_reason = cls.should_stop_followup(
            completeness_score=completeness_score,
            risk_score=risk_score,
            decision=decision,
            critical_missing_count=critical_missing_count
        )
        
        if should_stop:
            return {
                "questions": [],
                "stop_followup": True,
                "stop_reason": stop_reason,
                "stats": {
                    "completeness_score": completeness_score,
                    "risk_score": risk_score,
                    "critical_missing": critical_missing_count,
                    "total_missing": len(missing_fields)
                }
            }
        
        # Score and rank all questions
        scored_questions = cls.score_and_rank_questions(
            missing_fields=missing_fields,
            risk_score=risk_score,
            completeness_score=completeness_score
        )
        
        # Select questions based on adaptive rules
        selected_questions = cls.select_questions(
            scored_questions=scored_questions,
            completeness_score=completeness_score,
            max_questions=max_questions
        )
        
        return {
            "questions": selected_questions,
            "stop_followup": False,
            "stop_reason": None,
            "stats": {
                "completeness_score": completeness_score,
                "risk_score": risk_score,
                "critical_missing": critical_missing_count,
                "total_missing": len(missing_fields),
                "total_scored": len(scored_questions),
                "selected_count": len(selected_questions),
                "avg_value_score": round(
                    sum(q["value_score"] for q in selected_questions) / len(selected_questions), 3
                ) if selected_questions else 0.0
            }
        }    
    # ================================================================
    # FEATURE-3 ENHANCEMENTS (Additive - Backward Compatible)
    # ================================================================
    
    @classmethod
    def _load_rl_state(cls) -> Dict[str, Any]:
        """
        Load RL state from JSON file
        Returns empty dict if file doesn't exist or parsing fails
        """
        if not cls.RL_ENABLED:
            return {}
        
        try:
            if os.path.exists(cls.RL_STATE_FILE):
                with open(cls.RL_STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass  # Silent fallback
        
        return {}
    
    @classmethod
    def _save_rl_state(cls, state: Dict[str, Any]) -> None:
        """
        Save RL state to JSON file
        Silent failure - won't break if save fails
        """
        if not cls.RL_ENABLED:
            return
        
        try:
            os.makedirs(os.path.dirname(cls.RL_STATE_FILE), exist_ok=True)
            with open(cls.RL_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass  # Silent fallback
    
    @classmethod
    def _get_learned_reward(cls, field_name: str) -> float:
        """
        Get learned reward score for a field from RL history
        Returns 0.0 if no history exists (neutral)
        """
        try:
            rl_state = cls._load_rl_state()
            field_stats = rl_state.get(field_name, {})
            
            # Calculate average reward
            total_reward = field_stats.get("total_reward", 0.0)
            ask_count = field_stats.get("ask_count", 0)
            
            if ask_count > 0:
                return total_reward / ask_count
            
            return 0.0  # No history
        except Exception:
            return 0.0  # Fallback on any error
    
    @classmethod
    def _calculate_constraint_penalty(
        cls,
        field_name: str,
        criticality: str,
        risk_score: float,
        days_to_deadline: Optional[int]
    ) -> float:
        """
        Calculate constraint penalty based on risk and deadline
        
        Rules:
        - High risk + critical field: no penalty
        - High risk + non-critical: penalty = 1
        - Deadline < 3 days + non-regulatory: penalty = 2
        - Else: no penalty
        """
        try:
            penalty = 0.0
            
            # High risk constraints
            if risk_score >= 0.7:  # HIGH risk
                if criticality != "CRITICAL":
                    penalty = 1.0
            
            # Deadline constraints
            if days_to_deadline is not None and days_to_deadline < 3:
                if field_name not in cls.REGULATORY_CRITICAL_FIELDS:
                    penalty = max(penalty, 2.0)
            
            return penalty
        except Exception:
            return 0.0  # Fallback
    
    @classmethod
    def _calculate_duplicate_penalty(
        cls,
        field_name: str,
        previous_attempts: Optional[List[str]],
        force_critical: bool = False,
        unanswered_fields: Optional[List[str]] = None
    ) -> float:
        """
        Calculate penalty for previously asked questions.
        
        KEY CHANGE: Previously-asked-but-UNANSWERED fields get a BOOST (negative penalty)
        instead of being penalized. This ensures re-follow-ups prioritize unanswered questions.
        
        Args:
            field_name: Question field name
            previous_attempts: List of previously asked field names
            force_critical: If True, bypass penalty (reviewer override)
            unanswered_fields: Fields that were asked but NOT answered (should be boosted)
        
        Returns:
            Penalty score (negative = boost, 0.0 = no change, 1.0 = max penalty)
        """
        if force_critical:
            return 0.0
        
        if previous_attempts is None:
            return 0.0
        
        try:
            if field_name in previous_attempts:
                # BOOST previously asked but UNANSWERED fields (they need re-asking)
                if unanswered_fields and field_name in unanswered_fields:
                    return -0.3  # Negative penalty = boost priority
                # Penalize previously asked AND ANSWERED fields (don't re-ask)
                return 1.0
            return 0.0
        except Exception:
            return 0.0
    
    @classmethod
    def _apply_deadline_weighting(
        cls,
        field_name: str,
        criticality: str,
        base_weight: float,
        days_to_deadline: Optional[int]
    ) -> float:
        """
        Adjust criticality weight based on deadline pressure
        
        Rules:
        - If days < 3 and regulatory-critical: increase weight by 20%
        - If days < 3 and non-critical: decrease weight by 20%
        - Else: no change
        
        Args:
            field_name: Question field name
            criticality: Field criticality level
            base_weight: Original criticality weight
            days_to_deadline: Days until regulatory deadline
        
        Returns:
            Adjusted weight
        """
        if days_to_deadline is None or days_to_deadline >= 3:
            return base_weight
        
        try:
            # Urgent deadline (< 3 days)
            if field_name in cls.REGULATORY_CRITICAL_FIELDS:
                # Boost regulatory-critical questions
                return min(base_weight * 1.2, 1.0)
            elif criticality in ["LOW", "MEDIUM"]:
                # Reduce optional questions
                return base_weight * 0.8
            
            return base_weight
        except Exception:
            return base_weight
    
    @classmethod
    def _filter_resume_logic(
        cls,
        missing_fields: List[Dict[str, Any]],
        answered_fields: Optional[List[str]],
        reviewer_questions: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Resume Logic: Filter out already answered fields
        
        Args:
            missing_fields: Original missing fields list
            answered_fields: List of field names already answered
            reviewer_questions: List of reviewer-injected questions
        
        Returns:
            Filtered missing fields (excluding answered, unless force_critical)
        """
        if answered_fields is None:
            answered_fields = []
        
        # Build set of force_critical fields from reviewer
        force_critical_fields = set()
        if reviewer_questions:
            for rq in reviewer_questions:
                if rq.get("force_critical", False):
                    force_critical_fields.add(rq["field"])
        
        # Filter out answered fields (unless force_critical)
        filtered = []
        for field in missing_fields:
            field_name = field["field"]
            
            # Keep if not answered OR if force_critical
            if field_name not in answered_fields or field_name in force_critical_fields:
                filtered.append(field)
        
        return filtered
    
    @classmethod
    def _merge_reviewer_questions(
        cls,
        missing_fields: List[Dict[str, Any]],
        reviewer_questions: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Reviewer Question Injection: Merge reviewer-added questions
        
        Args:
            missing_fields: Original missing fields
            reviewer_questions: Reviewer-injected questions
                Format: [{"field": "...", "criticality": "...", "force_critical": bool}, ...]
        
        Returns:
            Merged list with reviewer questions added
        """
        if not reviewer_questions:
            return missing_fields
        
        # Build field names set
        existing_fields = {f["field"] for f in missing_fields}
        
        merged = list(missing_fields)
        
        for rq in reviewer_questions:
            field_name = rq["field"]
            
            # Add if not already in missing_fields
            if field_name not in existing_fields:
                merged.append({
                    "field": field_name,
                    "field_display": rq.get("field_display", field_name.replace("_", " ").title()),
                    "criticality": rq.get("criticality", "HIGH"),
                    "safety_impact": rq.get("safety_impact", "Reviewer requested"),
                    "category": rq.get("category", "Reviewer"),
                    "force_critical": rq.get("force_critical", False)
                })
        
        return merged
    
    @classmethod
    def calculate_enhanced_score(
        cls,
        field_name: str,
        criticality: str,
        risk_score: float,
        completeness_score: float,
        days_to_deadline: Optional[int] = None,
        previous_attempts: Optional[List[str]] = None,
        force_critical: bool = False
    ) -> Dict[str, float]:
        """
        Enhanced scoring with RL and constraints
        
        Formula:
            final_score = heuristic_score 
                        + (0.2 × learned_reward) 
                        - (0.5 × constraint_penalty) 
                        - (0.3 × duplicate_penalty)
        
        Args:
            field_name: Question field name
            criticality: CRITICAL/HIGH/MEDIUM/LOW
            risk_score: Case risk score
            completeness_score: Current completeness
            days_to_deadline: Days until regulatory deadline (optional)
            previous_attempts: Previously asked fields (optional)
            force_critical: Reviewer override flag
        
        Returns:
            {
                "heuristic_score": float,
                "learned_reward": float,
                "constraint_penalty": float,
                "duplicate_penalty": float,
                "final_score": float
            }
        """
        try:
            # Base heuristic score (existing logic)
            base_weight = cls.CRITICALITY_WEIGHTS.get(criticality, 0.25)
            
            # Apply deadline-aware weighting to base weight
            adjusted_weight = cls._apply_deadline_weighting(
                field_name, criticality, base_weight, days_to_deadline
            )
            
            risk_weight = cls.calculate_risk_weight(risk_score)
            urgency_factor = 1.0 - (completeness_score * 0.3)
            
            heuristic_score = adjusted_weight * risk_weight * urgency_factor
            
            # RL components (only if enabled)
            learned_reward = 0.0
            constraint_penalty = 0.0
            duplicate_penalty = 0.0
            
            if cls.RL_ENABLED:
                learned_reward = cls._get_learned_reward(field_name)
                constraint_penalty = cls._calculate_constraint_penalty(
                    field_name, criticality, risk_score, days_to_deadline
                )
                duplicate_penalty = cls._calculate_duplicate_penalty(
                    field_name, previous_attempts, force_critical
                )
            
            # Final score calculation
            final_score = (
                heuristic_score
                + (cls.RL_REWARD_WEIGHT * learned_reward)
                - (cls.RL_CONSTRAINT_WEIGHT * constraint_penalty)
                - (cls.RL_DUPLICATE_WEIGHT * duplicate_penalty)
            )
            
            # Ensure non-negative
            final_score = max(final_score, 0.0)
            
            return {
                "heuristic_score": round(heuristic_score, 3),
                "learned_reward": round(learned_reward, 3),
                "constraint_penalty": round(constraint_penalty, 3),
                "duplicate_penalty": round(duplicate_penalty, 3),
                "final_score": round(final_score, 3)
            }
            
        except Exception:
            # Fallback to heuristic-only on any error
            heuristic_score = cls.calculate_question_value(
                criticality, risk_score, completeness_score
            )
            return {
                "heuristic_score": heuristic_score,
                "learned_reward": 0.0,
                "constraint_penalty": 0.0,
                "duplicate_penalty": 0.0,
                "final_score": heuristic_score
            }
    
    @classmethod
    def update_rl_feedback(
        cls,
        field_name: str,
        answered: bool,
        completeness_increase: float = 0.0,
        is_critical: bool = False
    ) -> None:
        """
        Update RL state with feedback from follow-up attempt
        
        Reward rules:
        - +2 if answered
        - +3 if completeness increase > 20%
        - +5 if critical field answered
        - -1 if unanswered
        - -2 if unnecessary optional question
        
        Args:
            field_name: Question field name
            answered: Whether question was answered
            completeness_increase: Completeness improvement (0.0 to 1.0)
            is_critical: Whether field is critical
        """
        if not cls.RL_ENABLED:
            return
        
        try:
            # Calculate reward
            reward = 0.0
            
            if answered:
                reward += 2.0
                
                if completeness_increase > 0.20:
                    reward += 3.0
                
                if is_critical:
                    reward += 5.0
            else:
                reward -= 1.0
                
                # Penalize asking unnecessary optional questions
                if not is_critical:
                    reward -= 2.0
            
            # Load current state
            rl_state = cls._load_rl_state()
            
            # Update field stats
            if field_name not in rl_state:
                rl_state[field_name] = {
                    "total_reward": 0.0,
                    "ask_count": 0,
                    "answer_count": 0,
                    "last_updated": None
                }
            
            field_stats = rl_state[field_name]
            field_stats["total_reward"] += reward
            field_stats["ask_count"] += 1
            
            if answered:
                field_stats["answer_count"] += 1
            
            field_stats["last_updated"] = datetime.now().isoformat()
            
            # Save updated state
            cls._save_rl_state(rl_state)
            
        except Exception:
            pass  # Silent failure - won't break system
    
    @classmethod
    def generate_adaptive_questions_enhanced(
        cls,
        missing_fields: List[Dict[str, Any]],
        risk_score: float,
        completeness_score: float,
        decision: str,
        critical_missing_count: int,
        max_questions: int = 4,
        # New Feature-3 parameters (all optional for backward compatibility)
        answered_fields: Optional[List[str]] = None,
        reviewer_questions: Optional[List[Dict[str, Any]]] = None,
        days_to_deadline: Optional[int] = None,
        previous_attempts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced question generation with Feature-3 capabilities
        
        New Features:
        1. Resume Logic - filters out answered fields
        2. Reviewer Injection - merges reviewer questions
        3. Deadline Weighting - adjusts importance by deadline
        4. Duplicate Protection - penalizes repeated questions
        5. RL Learning - uses historical performance
        
        Backward Compatible: Falls back to heuristic-only if errors occur
        
        Args:
            (Same as generate_adaptive_questions, plus:)
            answered_fields: List of already answered field names
            reviewer_questions: Reviewer-injected questions
            days_to_deadline: Days until regulatory deadline
            previous_attempts: Previously asked field names
        
        Returns:
            Same format as generate_adaptive_questions
        """
        try:
            # GUARD: If no missing fields at all, no follow-up needed
            if not missing_fields:
                return {
                    "questions": [],
                    "stop_followup": True,
                    "stop_reason": "all_fields_complete",
                    "stats": {
                        "completeness_score": completeness_score,
                        "risk_score": risk_score,
                        "critical_missing": 0,
                        "total_missing": 0,
                        "resume_filtered": 0,
                        "reviewer_added": 0
                    }
                }

            # Feature-3.1: Resume Logic  
            filtered_fields = cls._filter_resume_logic(
                missing_fields, answered_fields, reviewer_questions
            )
            
            # Feature-3.2: Reviewer Question Injection
            merged_fields = cls._merge_reviewer_questions(
                filtered_fields, reviewer_questions
            )
            
            # Check stopping conditions (unchanged)
            should_stop, stop_reason = cls.should_stop_followup(
                completeness_score, risk_score, decision, critical_missing_count
            )
            
            if should_stop:
                return {
                    "questions": [],
                    "stop_followup": True,
                    "stop_reason": stop_reason,
                    "stats": {
                        "completeness_score": completeness_score,
                        "risk_score": risk_score,
                        "critical_missing": critical_missing_count,
                        "total_missing": len(merged_fields),
                        "resume_filtered": len(missing_fields) - len(filtered_fields),
                        "reviewer_added": len(merged_fields) - len(filtered_fields)
                    }
                }
            
            # Score all questions with enhanced scoring
            scored_questions = []
            
            for field in merged_fields:
                field_name = field["field"]
                criticality = field["criticality"]
                force_critical = field.get("force_critical", False)
                
                # Calculate enhanced score (with RL + constraints)
                score_breakdown = cls.calculate_enhanced_score(
                    field_name=field_name,
                    criticality=criticality,
                    risk_score=risk_score,
                    completeness_score=completeness_score,
                    days_to_deadline=days_to_deadline,
                    previous_attempts=previous_attempts,
                    force_critical=force_critical
                )
                
                # Get question text (LLM for CIOMS fields, None if Mistral fails)
                question_text = cls.resolve_question_text(
                    field_name=field_name,
                    field_display=field.get("field_display", field_name),
                )
                
                # Skip questions where Mistral failed (no generic fallback)
                if question_text is None:
                    logger.info(f"Skipping field '{field_name}' — no question text generated")
                    continue
                
                scored_questions.append({
                    "field": field_name,
                    "field_display": field.get("field_display", field_name),
                    "question": question_text,
                    "criticality": criticality,
                    "safety_impact": field.get("safety_impact", ""),
                    "value_score": score_breakdown["final_score"],  # Use final score
                    "category": field.get("category", "Unknown"),
                    "force_critical": force_critical,
                    # Include score breakdown for transparency
                    "score_breakdown": score_breakdown
                })
            
            # Sort by final score (descending)
            scored_questions.sort(key=lambda x: x["value_score"], reverse=True)
            
            # Select questions with safety checks
            selected_questions = cls._select_with_safety_checks(
                scored_questions=scored_questions,
                completeness_score=completeness_score,
                max_questions=max_questions
            )
            
            return {
                "questions": selected_questions,
                "stop_followup": False,
                "stop_reason": None,
                "stats": {
                    "completeness_score": completeness_score,
                    "risk_score": risk_score,
                    "critical_missing": critical_missing_count,
                    "total_missing": len(merged_fields),
                    "total_scored": len(scored_questions),
                    "selected_count": len(selected_questions),
                    "avg_value_score": round(
                        sum(q["value_score"] for q in selected_questions) / len(selected_questions), 3
                    ) if selected_questions else 0.0,
                    "resume_filtered": len(missing_fields) - len(filtered_fields),
                    "reviewer_added": len(merged_fields) - len(filtered_fields),
                    "rl_enabled": cls.RL_ENABLED
                }
            }
            
        except Exception:
            # FALLBACK: Use original heuristic-only method
            return cls.generate_adaptive_questions(
                missing_fields=missing_fields,
                risk_score=risk_score,
                completeness_score=completeness_score,
                decision=decision,
                critical_missing_count=critical_missing_count,
                max_questions=max_questions
            )
    
    @classmethod
    def _select_with_safety_checks(
        cls,
        scored_questions: List[Dict[str, Any]],
        completeness_score: float,
        max_questions: int
    ) -> List[Dict[str, Any]]:
        """
        Select questions with safety checks
        
        Safety Rules:
        - ALWAYS include all force_critical questions
        - ALWAYS include all CRITICAL safety questions
        - Respect max_questions limit
        - Prioritize by value_score
        """
        selected = []
        
        # Separate questions
        force_critical = [q for q in scored_questions if q.get("force_critical", False)]
        critical_safety = [q for q in scored_questions 
                          if q["criticality"] == "CRITICAL" and not q.get("force_critical", False)]
        other_questions = [q for q in scored_questions 
                          if q["criticality"] != "CRITICAL" and not q.get("force_critical", False)]
        
        # Safety Rule 1: ALWAYS include force_critical
        selected.extend(force_critical)
        
        # Safety Rule 2: ALWAYS include CRITICAL
        selected.extend(critical_safety)
        
        # Add other questions up to max limit
        remaining_slots = max_questions - len(selected)
        if remaining_slots > 0:
            selected.extend(other_questions[:remaining_slots])
        
        # Enforce max limit
        return selected[:max_questions]