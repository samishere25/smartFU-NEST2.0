"""
Confidence Attribution Map
Explains exactly how each piece of information contributed to confidence gain
"""

from typing import Dict, List, Any
from datetime import datetime


class ConfidenceAttributionMapper:
    """
    Breaks down confidence into per-field contributions
    
    Shows: "Getting suspect_drug increased confidence by +40%"
    """
    
    # Field importance weights for attribution
    FIELD_WEIGHTS = {
        # Critical fields - highest impact
        'suspect_drug': 0.45,       # 45% of total confidence
        'adverse_event': 0.40,      # 40% (but usually already present)
        'patient_age': 0.15,
        'event_date': 0.12,
        'drug_dose': 0.10,
        'event_outcome': 0.10,
        
        # Important fields - medium impact
        'patient_sex': 0.08,
        'drug_route': 0.07,
        'concomitant_drugs': 0.09,
        'medical_history': 0.08,
        'rechallenge': 0.12,
        
        # Supporting fields - lower impact
        'indication': 0.05,
        'dose_frequency': 0.04,
        'lot_number': 0.03,
        'reporter_name': 0.02
    }
    
    def __init__(self):
        self.attribution_history = []
    
    def calculate_field_attribution(
        self,
        field_name: str,
        field_value: Any,
        case_context: Dict
    ) -> Dict[str, Any]:
        """
        Calculate how much this field contributed to confidence
        
        Returns attribution with reasoning
        """
        # Base contribution from field weight
        base_weight = self.FIELD_WEIGHTS.get(field_name, 0.03)
        
        # Adjust based on context
        adjusted_weight = self._adjust_for_context(
            field_name, field_value, case_context
        )
        
        # Calculate actual contribution (as percentage)
        contribution = adjusted_weight * 100
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            field_name, field_value, contribution, case_context
        )
        
        # Determine impact level
        if contribution >= 30:
            impact = 'CRITICAL'
        elif contribution >= 15:
            impact = 'HIGH'
        elif contribution >= 5:
            impact = 'MEDIUM'
        else:
            impact = 'LOW'
        
        return {
            'field': field_name,
            'value': str(field_value)[:50],  # Truncate long values
            'contribution_percent': round(contribution, 1),
            'impact_level': impact,
            'reasoning': reasoning,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _adjust_for_context(
        self,
        field_name: str,
        field_value: Any,
        context: Dict
    ) -> float:
        """
        Adjust field weight based on case context
        """
        base_weight = self.FIELD_WEIGHTS.get(field_name, 0.03)
        
        # Boost for high-risk cases
        risk_score = context.get('risk_score', 0.5)
        if risk_score > 0.7:
            # High risk cases need more certainty
            if field_name in ['suspect_drug', 'event_date', 'drug_dose']:
                base_weight *= 1.3
        
        # Boost if many fields are missing
        missing_count = context.get('missing_count', 0)
        if missing_count > 5:
            # Each field is more valuable when few are present
            base_weight *= 1.2
        
        # Boost for serious events
        is_serious = context.get('is_serious', False)
        if is_serious and field_name in ['suspect_drug', 'event_outcome', 'rechallenge']:
            base_weight *= 1.25
        
        return min(0.50, base_weight)  # Cap at 50%
    
    def _generate_reasoning(
        self,
        field_name: str,
        field_value: Any,
        contribution: float,
        context: Dict
    ) -> str:
        """
        Generate human-readable explanation of contribution
        """
        reasons = []
        
        # Field-specific reasoning
        field_reasons = {
            'suspect_drug': [
                "Essential for causality assessment",
                "Cannot proceed without drug identification",
                "Highest regulatory priority"
            ],
            'event_date': [
                "Establishes temporal relationship",
                "Required for causality analysis",
                "Helps identify signal timing"
            ],
            'drug_dose': [
                "Supports dose-response relationship",
                "Important for severity assessment",
                "Helps rule out overdose"
            ],
            'patient_age': [
                "Critical demographic factor",
                "Affects risk stratification",
                "Age-specific reactions possible"
            ],
            'concomitant_drugs': [
                "Identifies potential interactions",
                "Rules out confounding factors",
                "Important for differential diagnosis"
            ]
        }
        
        reason_list = field_reasons.get(field_name, [
            f"Provides additional context for {field_name}",
            "Reduces uncertainty in safety assessment"
        ])
        
        # Add context-specific reasons
        if context.get('risk_score', 0) > 0.7:
            reason_list.append("Critical due to high risk score")
        
        if context.get('is_serious', False):
            reason_list.append("Important for serious adverse event")
        
        # Select most relevant reasons
        selected_reasons = reason_list[:2]
        
        return " | ".join(selected_reasons)
    
    def calculate_iteration_attribution(
        self,
        before_state: Dict,
        after_state: Dict,
        fields_added: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate attribution for entire iteration
        
        Shows what changed and total impact
        """
        before_confidence = before_state.get('confidence', 0.0)
        after_confidence = after_state.get('confidence', 0.0)
        total_gain = after_confidence - before_confidence
        
        # Calculate per-field attributions
        field_attributions = []
        
        for field in fields_added:
            field_value = after_state.get(field)
            
            attribution = self.calculate_field_attribution(
                field, field_value, after_state
            )
            
            field_attributions.append(attribution)
        
        # Sort by contribution
        field_attributions.sort(
            key=lambda x: x['contribution_percent'],
            reverse=True
        )
        
        # Calculate percentages that sum to total gain
        total_weight = sum(
            self.FIELD_WEIGHTS.get(f, 0.03) for f in fields_added
        )
        
        for attr in field_attributions:
            field = attr['field']
            field_weight = self.FIELD_WEIGHTS.get(field, 0.03)
            
            # Proportion of total gain
            attr['confidence_gain'] = round(
                (field_weight / total_weight) * total_gain * 100,
                1
            )
        
        return {
            'iteration_summary': {
                'before_confidence': round(before_confidence * 100, 1),
                'after_confidence': round(after_confidence * 100, 1),
                'total_gain': round(total_gain * 100, 1),
                'fields_added': len(fields_added)
            },
            'field_attributions': field_attributions,
            'top_contributor': field_attributions[0] if field_attributions else None
        }
    
    def generate_attribution_report(
        self,
        case_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate complete attribution report for case
        
        Shows full journey from start to finish
        """
        iterations = []
        cumulative_contributions = {}
        
        for i, iteration in enumerate(case_history):
            # Calculate iteration attribution
            if i == 0:
                before = {'confidence': 0.0}
            else:
                before = case_history[i-1]
            
            attribution = self.calculate_iteration_attribution(
                before,
                iteration,
                iteration.get('fields_added', [])
            )
            
            iterations.append({
                'iteration_number': i + 1,
                'attribution': attribution
            })
            
            # Track cumulative contributions
            for field_attr in attribution['field_attributions']:
                field = field_attr['field']
                gain = field_attr.get('confidence_gain', 0)
                
                if field not in cumulative_contributions:
                    cumulative_contributions[field] = {
                        'total_contribution': 0,
                        'appearances': 0
                    }
                
                cumulative_contributions[field]['total_contribution'] += gain
                cumulative_contributions[field]['appearances'] += 1
        
        # Sort cumulative by total contribution
        cumulative_sorted = sorted(
            cumulative_contributions.items(),
            key=lambda x: x[1]['total_contribution'],
            reverse=True
        )
        
        return {
            'case_summary': {
                'total_iterations': len(iterations),
                'initial_confidence': case_history[0].get('confidence', 0) * 100 if case_history else 0,
                'final_confidence': case_history[-1].get('confidence', 0) * 100 if case_history else 0,
                'total_gain': (case_history[-1].get('confidence', 0) - case_history[0].get('confidence', 0)) * 100 if len(case_history) > 1 else 0
            },
            'iteration_breakdown': iterations,
            'cumulative_contributions': [
                {
                    'field': field,
                    'total_contribution': round(data['total_contribution'], 1),
                    'appearances': data['appearances']
                }
                for field, data in cumulative_sorted
            ],
            'top_3_contributors': [
                {
                    'field': field,
                    'contribution': round(data['total_contribution'], 1)
                }
                for field, data in cumulative_sorted[:3]
            ]
        }
    
    def create_visual_attribution(
        self,
        attribution_data: Dict
    ) -> Dict[str, Any]:
        """
        Create visualization-ready data for frontend
        
        Returns waterfall chart data
        """
        iterations = attribution_data['iteration_breakdown']
        
        # Waterfall chart data
        waterfall_data = []
        cumulative = attribution_data['case_summary']['initial_confidence']
        
        waterfall_data.append({
            'label': 'Initial',
            'value': cumulative,
            'type': 'start'
        })
        
        for iter_data in iterations:
            for field_attr in iter_data['attribution']['field_attributions']:
                gain = field_attr.get('confidence_gain', 0)
                cumulative += gain
                
                waterfall_data.append({
                    'label': field_attr['field'],
                    'value': gain,
                    'cumulative': cumulative,
                    'type': 'increase',
                    'iteration': iter_data['iteration_number']
                })
        
        waterfall_data.append({
            'label': 'Final',
            'value': cumulative,
            'type': 'end'
        })
        
        return {
            'chart_type': 'waterfall',
            'data': waterfall_data,
            'title': 'Confidence Attribution Waterfall',
            'x_axis': 'Information Added',
            'y_axis': 'Confidence (%)'
        }


# Convenience functions
def calculate_attribution(before: Dict, after: Dict, fields: List[str]) -> Dict:
    """Quick attribution calculation"""
    mapper = ConfidenceAttributionMapper()
    return mapper.calculate_iteration_attribution(before, after, fields)


def generate_full_report(case_history: List[Dict]) -> Dict:
    """Quick full report generation"""
    mapper = ConfidenceAttributionMapper()
    return mapper.generate_attribution_report(case_history)
