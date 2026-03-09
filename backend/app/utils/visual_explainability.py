"""
Visual Explainability System
Generates charts, graphs, and visual explanations for AI decisions
"""

from typing import Dict, List, Any, Tuple
import json


class VisualExplainer:
    """
    Creates visual explanations for ML predictions and AI decisions
    Outputs chart data in JSON format for frontend rendering
    """
    
    def generate_feature_importance_chart(
        self,
        feature_importance: Dict[str, float],
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Generate horizontal bar chart data for feature importance
        
        Returns Chart.js compatible format
        """
        # Sort by importance
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        labels = [f.replace('_', ' ').title() for f, _ in sorted_features]
        values = [round(v * 100, 1) for _, v in sorted_features]
        
        # Color coding
        colors = []
        for v in values:
            if v > 15:
                colors.append('rgba(220, 53, 69, 0.8)')  # Red - very important
            elif v > 10:
                colors.append('rgba(255, 193, 7, 0.8)')  # Yellow - important
            else:
                colors.append('rgba(40, 167, 69, 0.8)')  # Green - moderate
        
        return {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Feature Importance (%)',
                    'data': values,
                    'backgroundColor': colors,
                    'borderWidth': 1
                }]
            },
            'options': {
                'indexAxis': 'y',
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': 'Top 10 Most Important Features'
                    },
                    'legend': {
                        'display': False
                    }
                },
                'scales': {
                    'x': {
                        'beginAtZero': True,
                        'max': max(values) * 1.2,
                        'title': {
                            'display': True,
                            'text': 'Importance (%)'
                        }
                    }
                }
            }
        }
    
    def generate_confidence_gauge(
        self,
        confidence: float,
        threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Generate gauge chart for confidence visualization
        
        Shows current confidence vs threshold
        """
        # Determine color based on confidence level
        if confidence >= threshold:
            color = 'rgba(40, 167, 69, 0.8)'  # Green
            status = 'EXCELLENT'
        elif confidence >= threshold * 0.9:
            color = 'rgba(255, 193, 7, 0.8)'  # Yellow
            status = 'GOOD'
        elif confidence >= threshold * 0.7:
            color = 'rgba(255, 152, 0, 0.8)'  # Orange
            status = 'FAIR'
        else:
            color = 'rgba(220, 53, 69, 0.8)'  # Red
            status = 'LOW'
        
        return {
            'type': 'doughnut',
            'data': {
                'labels': ['Confidence', 'Remaining'],
                'datasets': [{
                    'data': [
                        round(confidence * 100, 1),
                        round((1 - confidence) * 100, 1)
                    ],
                    'backgroundColor': [color, 'rgba(200, 200, 200, 0.3)'],
                    'borderWidth': 0
                }]
            },
            'options': {
                'rotation': -90,
                'circumference': 180,
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': f'Safety Confidence: {status}'
                    },
                    'legend': {
                        'display': False
                    },
                    'tooltip': {
                        'callbacks': {
                            'label': '(ctx) => ctx.label + ": " + ctx.parsed + "%"'
                        }
                    }
                }
            },
            'centerText': {
                'value': f'{confidence:.0%}',
                'threshold': f'{threshold:.0%}'
            }
        }
    
    def generate_decision_flow_diagram(
        self,
        agent_messages: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate Mermaid.js flowchart of AI decision process
        """
        mermaid_code = "graph TD\n"
        mermaid_code += "    Start[Start Analysis] --> A[Data Completeness]\n"
        
        for i, msg in enumerate(agent_messages):
            agent = msg.get('agent', f'Agent{i}')
            
            if agent == 'DataCompleteness':
                mermaid_code += f"    A -->|Missing Fields| B[Risk Assessment]\n"
            elif agent == 'RiskAssessment':
                risk = msg.get('risk_score', 0)
                category = msg.get('category', 'UNKNOWN')
                mermaid_code += f"    B -->|Risk: {risk:.2f} ({category})| C[Response Strategy]\n"
            elif agent == 'ResponseStrategy':
                prob = msg.get('response_probability', 0)
                mermaid_code += f"    C -->|Response: {prob:.0%}| D[Escalation]\n"
            elif agent == 'Escalation':
                decision = msg.get('decision', 'UNKNOWN')
                mermaid_code += f"    D -->|{decision}| End[Complete]\n"
        
        mermaid_code += "    \n"
        mermaid_code += "    style A fill:#e3f2fd\n"
        mermaid_code += "    style B fill:#fff3e0\n"
        mermaid_code += "    style C fill:#f3e5f5\n"
        mermaid_code += "    style D fill:#e8f5e9\n"
        mermaid_code += "    style End fill:#c8e6c9\n"
        
        return {
            'type': 'mermaid',
            'code': mermaid_code
        }
    
    def generate_confidence_evolution_chart(
        self,
        confidence_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Line chart showing how confidence improved over iterations
        """
        labels = [f"Iteration {h['iteration']}" for h in confidence_history]
        confidence_values = [round(h['confidence'] * 100, 1) for h in confidence_history]
        
        # Add threshold line
        threshold = 85  # 85% threshold
        
        return {
            'type': 'line',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Safety Confidence',
                        'data': confidence_values,
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                        'tension': 0.3,
                        'fill': True
                    },
                    {
                        'label': 'Threshold (85%)',
                        'data': [threshold] * len(labels),
                        'borderColor': 'rgba(220, 53, 69, 1)',
                        'borderDash': [5, 5],
                        'borderWidth': 2,
                        'pointRadius': 0,
                        'fill': False
                    }
                ]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': 'Confidence Evolution Across Iterations'
                    }
                },
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'max': 100,
                        'title': {
                            'display': True,
                            'text': 'Confidence (%)'
                        }
                    }
                }
            }
        }
    
    def generate_prediction_breakdown(
        self,
        prediction: float,
        components: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Stacked bar chart showing how different factors contribute to prediction
        """
        labels = [k.replace('_', ' ').title() for k in components.keys()]
        values = [round(v * 100, 1) for v in components.values()]
        
        colors = [
            'rgba(255, 99, 132, 0.8)',
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)',
            'rgba(153, 102, 255, 0.8)'
        ]
        
        return {
            'type': 'bar',
            'data': {
                'labels': ['Prediction Breakdown'],
                'datasets': [
                    {
                        'label': labels[i],
                        'data': [values[i]],
                        'backgroundColor': colors[i % len(colors)]
                    } for i in range(len(labels))
                ]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': f'Response Probability: {prediction:.0%}'
                    }
                },
                'scales': {
                    'x': {
                        'stacked': True
                    },
                    'y': {
                        'stacked': True,
                        'max': 100,
                        'title': {
                            'display': True,
                            'text': 'Contribution (%)'
                        }
                    }
                }
            }
        }
    
    def generate_confidence_intervals(
        self,
        prediction: float,
        std_error: float = 0.05
    ) -> Dict[str, Any]:
        """
        Show prediction with confidence intervals (uncertainty)
        """
        # Calculate 95% confidence interval
        margin = 1.96 * std_error
        lower = max(0, prediction - margin)
        upper = min(1, prediction + margin)
        
        return {
            'prediction': round(prediction, 3),
            'confidence_interval_95': {
                'lower': round(lower, 3),
                'upper': round(upper, 3)
            },
            'uncertainty': round(std_error, 3),
            'interpretation': self._interpret_uncertainty(std_error),
            'chart': {
                'type': 'scatter',
                'data': {
                    'datasets': [{
                        'label': 'Prediction',
                        'data': [{'x': 0, 'y': prediction * 100}],
                        'backgroundColor': 'rgba(54, 162, 235, 1)',
                        'pointRadius': 8
                    }, {
                        'label': '95% Confidence Interval',
                        'data': [
                            {'x': 0, 'y': lower * 100},
                            {'x': 0, 'y': upper * 100}
                        ],
                        'showLine': True,
                        'borderColor': 'rgba(255, 99, 132, 0.5)',
                        'borderWidth': 3,
                        'pointRadius': 0,
                        'fill': False
                    }]
                },
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': 'Prediction with Uncertainty'
                        }
                    },
                    'scales': {
                        'y': {
                            'min': 0,
                            'max': 100,
                            'title': {
                                'display': True,
                                'text': 'Response Probability (%)'
                            }
                        },
                        'x': {
                            'display': False
                        }
                    }
                }
            }
        }
    
    def _interpret_uncertainty(self, std_error: float) -> str:
        """Interpret uncertainty level"""
        if std_error < 0.05:
            return "HIGH CONFIDENCE - Prediction is reliable"
        elif std_error < 0.10:
            return "MODERATE CONFIDENCE - Prediction has some uncertainty"
        else:
            return "LOW CONFIDENCE - Prediction is uncertain"
    
    def create_complete_dashboard(
        self,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create complete visual dashboard with all charts
        """
        dashboard = {
            'title': 'AI Decision Explanation Dashboard',
            'case_id': analysis_result.get('case_id'),
            'timestamp': analysis_result.get('timestamp'),
            'visualizations': {}
        }
        
        # Feature importance (if available)
        if 'feature_importance' in analysis_result:
            dashboard['visualizations']['feature_importance'] = \
                self.generate_feature_importance_chart(
                    analysis_result['feature_importance']
                )
        
        # Confidence gauge
        if 'confidence' in analysis_result:
            dashboard['visualizations']['confidence_gauge'] = \
                self.generate_confidence_gauge(
                    analysis_result['confidence']
                )
        
        # Decision flow
        if 'messages' in analysis_result:
            dashboard['visualizations']['decision_flow'] = \
                self.generate_decision_flow_diagram(
                    analysis_result['messages']
                )
        
        # Confidence evolution (if available)
        if 'confidence_history' in analysis_result:
            dashboard['visualizations']['confidence_evolution'] = \
                self.generate_confidence_evolution_chart(
                    analysis_result['confidence_history']
                )
        
        # Prediction breakdown
        if 'response_probability' in analysis_result:
            components = {
                'reporter_type': 0.35,
                'data_completeness': 0.25,
                'risk_level': 0.20,
                'temporal_factors': 0.20
            }
            dashboard['visualizations']['prediction_breakdown'] = \
                self.generate_prediction_breakdown(
                    analysis_result['response_probability'],
                    components
                )
        
        # Confidence intervals
        if 'response_probability' in analysis_result:
            dashboard['visualizations']['confidence_intervals'] = \
                self.generate_confidence_intervals(
                    analysis_result['response_probability']
                )
        
        return dashboard


# Convenience function
def create_visual_explanation(analysis_result: Dict) -> Dict:
    """Quick access to visual explanations"""
    explainer = VisualExplainer()
    return explainer.create_complete_dashboard(analysis_result)
