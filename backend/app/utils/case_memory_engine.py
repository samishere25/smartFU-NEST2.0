"""
Case Memory & Micro-Learning Engine
Learns from every completed case and reuses successful strategies
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from collections import defaultdict
import json


class CasePattern:
    """Represents a pattern of case characteristics"""
    
    def __init__(self, case_data: Dict):
        self.reporter_type = case_data.get('reporter_type', 'UNKNOWN')
        self.event_severity = self._categorize_severity(case_data)
        self.initial_completeness = case_data.get('initial_completeness', 0.5)
        self.risk_score = case_data.get('risk_score', 0.5)
        self.missing_fields_count = case_data.get('missing_count', 0)
        self.event_type = self._categorize_event(case_data.get('adverse_event', ''))
    
    def _categorize_severity(self, case_data: Dict) -> str:
        """Categorize case severity"""
        if case_data.get('is_serious', False):
            return 'SERIOUS'
        elif case_data.get('risk_score', 0) > 0.7:
            return 'HIGH'
        elif case_data.get('risk_score', 0) > 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _categorize_event(self, event: str) -> str:
        """Categorize event type"""
        event_lower = event.lower()
        
        if any(word in event_lower for word in ['death', 'died', 'fatal']):
            return 'DEATH'
        elif any(word in event_lower for word in ['anaphyl', 'shock', 'allerg']):
            return 'ALLERGIC'
        elif any(word in event_lower for word in ['hospital', 'admit']):
            return 'HOSPITALIZATION'
        elif any(word in event_lower for word in ['bleed', 'hemorrh']):
            return 'BLEEDING'
        else:
            return 'OTHER'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'reporter_type': self.reporter_type,
            'event_severity': self.event_severity,
            'initial_completeness': self.initial_completeness,
            'risk_score': self.risk_score,
            'missing_fields_count': self.missing_fields_count,
            'event_type': self.event_type
        }
    
    def similarity_score(self, other: 'CasePattern') -> float:
        """
        Calculate similarity between two case patterns
        
        Returns score 0-1 (1 = identical)
        """
        score = 0.0
        
        # Reporter type match (30% weight)
        if self.reporter_type == other.reporter_type:
            score += 0.30
        
        # Severity match (25% weight)
        if self.event_severity == other.event_severity:
            score += 0.25
        
        # Event type match (20% weight)
        if self.event_type == other.event_type:
            score += 0.20
        
        # Completeness similarity (15% weight)
        completeness_diff = abs(self.initial_completeness - other.initial_completeness)
        score += (1 - completeness_diff) * 0.15
        
        # Risk similarity (10% weight)
        risk_diff = abs(self.risk_score - other.risk_score)
        score += (1 - risk_diff) * 0.10
        
        return score


class SuccessfulStrategy:
    """Represents a strategy that worked for a case"""
    
    def __init__(self, strategy_data: Dict):
        self.channel = strategy_data.get('channel', 'email')
        self.timing = strategy_data.get('timing', 'normal')
        self.questions_asked = strategy_data.get('questions_asked', [])
        self.question_count = len(self.questions_asked)
        self.iterations_needed = strategy_data.get('iterations', 1)
        self.confidence_threshold = strategy_data.get('confidence_threshold', 0.85)
    
    def to_dict(self) -> Dict:
        return {
            'channel': self.channel,
            'timing': self.timing,
            'questions_asked': self.questions_asked,
            'question_count': self.question_count,
            'iterations_needed': self.iterations_needed,
            'confidence_threshold': self.confidence_threshold
        }


class CaseMemory:
    """Stores completed cases with their patterns and outcomes"""
    
    def __init__(self, case_id: str, pattern: CasePattern, strategy: SuccessfulStrategy, outcome: Dict):
        self.case_id = case_id
        self.pattern = pattern
        self.strategy = strategy
        self.outcome = outcome
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            'case_id': self.case_id,
            'pattern': self.pattern.to_dict(),
            'strategy': self.strategy.to_dict(),
            'outcome': self.outcome,
            'created_at': self.created_at.isoformat()
        }


class MicroLearningEngine:
    """
    Learns from completed cases and recommends strategies
    
    Features:
    - Pattern matching (find similar past cases)
    - Strategy recommendation (reuse what worked)
    - Success rate tracking
    - Continuous improvement
    """
    
    def __init__(self, similarity_threshold: float = 0.70):
        self.memory_bank: List[CaseMemory] = []
        self.similarity_threshold = similarity_threshold
        self.strategy_performance = defaultdict(lambda: {'success': 0, 'total': 0})
    
    def store_case_memory(
        self,
        case_id: str,
        case_data: Dict,
        strategy_used: Dict,
        outcome: Dict
    ) -> CaseMemory:
        """
        Store a completed case in memory
        
        Args:
            case_id: Unique case identifier
            case_data: Case characteristics
            strategy_used: Strategy that was used
            outcome: Results (success, response rate, etc.)
        
        Returns:
            CaseMemory object
        """
        # Create pattern
        pattern = CasePattern(case_data)
        
        # Create strategy
        strategy = SuccessfulStrategy(strategy_used)
        
        # Create memory
        memory = CaseMemory(case_id, pattern, strategy, outcome)
        
        # Store
        self.memory_bank.append(memory)
        
        # Update performance tracking
        strategy_key = f"{strategy.channel}_{strategy.timing}"
        self.strategy_performance[strategy_key]['total'] += 1
        if outcome.get('success', False):
            self.strategy_performance[strategy_key]['success'] += 1
        
        return memory
    
    def find_similar_cases(
        self,
        new_case_pattern: CasePattern,
        top_n: int = 5
    ) -> List[Tuple[CaseMemory, float]]:
        """
        Find similar cases from memory bank
        
        Returns list of (CaseMemory, similarity_score) tuples
        """
        similarities = []
        
        for memory in self.memory_bank:
            similarity = new_case_pattern.similarity_score(memory.pattern)
            
            if similarity >= self.similarity_threshold:
                similarities.append((memory, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_n]
    
    def recommend_strategy(
        self,
        new_case_data: Dict
    ) -> Dict[str, Any]:
        """
        Recommend strategy based on similar past cases
        
        Returns recommended strategy with confidence
        """
        # Create pattern for new case
        new_pattern = CasePattern(new_case_data)
        
        # Find similar cases
        similar_cases = self.find_similar_cases(new_pattern, top_n=10)
        
        if not similar_cases:
            return {
                'recommendation_available': False,
                'reason': 'No similar cases in memory',
                'similar_case_count': 0,
                'use_default_strategy': True
            }
        
        # Analyze strategies from similar cases
        strategy_votes = defaultdict(lambda: {
            'count': 0,
            'total_similarity': 0.0,
            'success_rate': 0.0,
            'avg_iterations': 0.0,
            'examples': []
        })
        
        for memory, similarity in similar_cases:
            strategy_key = f"{memory.strategy.channel}_{memory.strategy.timing}"
            
            strategy_votes[strategy_key]['count'] += 1
            strategy_votes[strategy_key]['total_similarity'] += similarity
            strategy_votes[strategy_key]['avg_iterations'] += memory.strategy.iterations_needed
            strategy_votes[strategy_key]['examples'].append({
                'case_id': memory.case_id,
                'similarity': round(similarity, 2),
                'outcome': memory.outcome
            })
            
            # Success rate
            if memory.outcome.get('success', False):
                strategy_votes[strategy_key]['success_rate'] += 1
        
        # Calculate averages and scores
        for key, data in strategy_votes.items():
            count = data['count']
            data['avg_similarity'] = data['total_similarity'] / count
            data['success_rate'] = data['success_rate'] / count
            data['avg_iterations'] = data['avg_iterations'] / count
            
            # Overall score (weighted)
            data['score'] = (
                data['avg_similarity'] * 0.3 +
                data['success_rate'] * 0.5 +
                (1 / data['avg_iterations']) * 0.2  # Prefer fewer iterations
            )
        
        # Get best strategy
        best_strategy_key = max(strategy_votes.items(), key=lambda x: x[1]['score'])[0]
        best_strategy_data = strategy_votes[best_strategy_key]
        
        # Parse strategy key
        channel, timing = best_strategy_key.split('_')
        
        # Get example questions from similar cases
        example_questions = []
        for memory, _ in similar_cases[:3]:
            example_questions.extend(memory.strategy.questions_asked)
        
        # Deduplicate
        unique_questions = list(set(example_questions))[:5]
        
        return {
            'recommendation_available': True,
            'similar_case_count': len(similar_cases),
            'confidence': round(best_strategy_data['score'], 2),
            'recommended_strategy': {
                'channel': channel,
                'timing': timing,
                'expected_iterations': round(best_strategy_data['avg_iterations']),
                'success_probability': round(best_strategy_data['success_rate'], 2),
                'similar_cases_used': best_strategy_data['count'],
                'avg_similarity': round(best_strategy_data['avg_similarity'], 2)
            },
            'suggested_questions': unique_questions,
            'reasoning': self._generate_recommendation_reasoning(
                best_strategy_data, similar_cases
            ),
            'example_cases': best_strategy_data['examples'][:3]
        }
    
    def _generate_recommendation_reasoning(
        self,
        strategy_data: Dict,
        similar_cases: List[Tuple[CaseMemory, float]]
    ) -> str:
        """Generate human-readable reasoning"""
        
        count = strategy_data['count']
        success_rate = strategy_data['success_rate']
        avg_similarity = strategy_data['avg_similarity']
        
        reasoning = f"Based on {count} similar cases (avg similarity: {avg_similarity:.0%}), "
        reasoning += f"this strategy achieved {success_rate:.0%} success rate. "
        
        if success_rate > 0.80:
            reasoning += "Highly recommended - proven effective."
        elif success_rate > 0.60:
            reasoning += "Recommended - good track record."
        else:
            reasoning += "Moderate confidence - limited historical data."
        
        return reasoning
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get statistics about what the system has learned
        """
        if not self.memory_bank:
            return {
                'total_cases_learned': 0,
                'learning_enabled': False
            }
        
        # Calculate stats
        total_cases = len(self.memory_bank)
        successful_cases = sum(1 for m in self.memory_bank if m.outcome.get('success', False))
        
        # Pattern distribution
        pattern_dist = defaultdict(int)
        for memory in self.memory_bank:
            pattern_key = f"{memory.pattern.reporter_type}_{memory.pattern.event_severity}"
            pattern_dist[pattern_key] += 1
        
        # Strategy performance
        strategy_stats = []
        for strategy_key, perf in self.strategy_performance.items():
            if perf['total'] > 0:
                strategy_stats.append({
                    'strategy': strategy_key,
                    'success_rate': round(perf['success'] / perf['total'], 2),
                    'total_uses': perf['total']
                })
        
        # Sort by success rate
        strategy_stats.sort(key=lambda x: x['success_rate'], reverse=True)
        
        return {
            'total_cases_learned': total_cases,
            'successful_cases': successful_cases,
            'overall_success_rate': round(successful_cases / total_cases, 2) if total_cases > 0 else 0,
            'learning_enabled': True,
            'pattern_coverage': len(pattern_dist),
            'top_patterns': sorted(
                pattern_dist.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'strategy_performance': strategy_stats[:10],
            'memory_bank_size': total_cases
        }
    
    def export_memory_bank(self) -> str:
        """Export memory bank as JSON"""
        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'total_cases': len(self.memory_bank),
            'memories': [m.to_dict() for m in self.memory_bank]
        }
        return json.dumps(data, indent=2)
    
    def import_memory_bank(self, json_data: str):
        """Import memory bank from JSON"""
        data = json.loads(json_data)
        
        for memory_dict in data['memories']:
            pattern = CasePattern(memory_dict['pattern'])
            strategy = SuccessfulStrategy(memory_dict['strategy'])
            memory = CaseMemory(
                memory_dict['case_id'],
                pattern,
                strategy,
                memory_dict['outcome']
            )
            self.memory_bank.append(memory)


# Convenience functions
def store_successful_case(case_id: str, case_data: Dict, strategy: Dict, outcome: Dict, engine: MicroLearningEngine):
    """Quick case storage"""
    return engine.store_case_memory(case_id, case_data, strategy, outcome)


def get_strategy_recommendation(case_data: Dict, engine: MicroLearningEngine) -> Dict:
    """Quick strategy recommendation"""
    return engine.recommend_strategy(case_data)
