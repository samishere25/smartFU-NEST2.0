"""
Pre-emptive Safety Readiness Engine
Proactively adjusts system behavior when signals are detected
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import numpy as np


class ReadinessLevel(Enum):
    """System readiness levels"""
    NORMAL = "normal"           # Business as usual
    ELEVATED = "elevated"       # Increased monitoring
    HIGH = "high"               # Proactive measures
    CRITICAL = "critical"       # Maximum response mode


class ReadinessProfile:
    """Configuration profile for each readiness level"""
    
    PROFILES = {
        ReadinessLevel.NORMAL: {
            'confidence_threshold': 0.85,
            'max_iterations': 3,
            'priority_channel': 'email',
            'response_timeout_hours': 168,  # 7 days
            'escalation_threshold': 0.70,
            'auto_escalate': False,
            'question_limit': 5
        },
        ReadinessLevel.ELEVATED: {
            'confidence_threshold': 0.82,   # Slightly lower
            'max_iterations': 3,
            'priority_channel': 'email',
            'response_timeout_hours': 120,  # 5 days
            'escalation_threshold': 0.65,
            'auto_escalate': False,
            'question_limit': 5
        },
        ReadinessLevel.HIGH: {
            'confidence_threshold': 0.80,   # Lower threshold
            'max_iterations': 4,            # More attempts
            'priority_channel': 'phone',    # Switch to phone
            'response_timeout_hours': 72,   # 3 days
            'escalation_threshold': 0.60,
            'auto_escalate': True,          # Auto-escalate
            'question_limit': 4             # Fewer questions (focus on critical)
        },
        ReadinessLevel.CRITICAL: {
            'confidence_threshold': 0.75,   # Even lower
            'max_iterations': 5,            # Maximum attempts
            'priority_channel': 'phone',
            'response_timeout_hours': 24,   # 1 day only!
            'escalation_threshold': 0.50,
            'auto_escalate': True,
            'question_limit': 3,            # Only critical questions
            'immediate_review': True
        }
    }
    
    @classmethod
    def get_profile(cls, level: ReadinessLevel) -> Dict[str, Any]:
        """Get configuration for readiness level"""
        return cls.PROFILES[level].copy()


class SignalTrendAnalyzer:
    """
    Analyzes signal trends to determine if readiness should increase
    """
    
    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
    
    def analyze_trend(
        self,
        historical_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze if signal is trending up
        
        Args:
            historical_data: List of {date, count} for signal
        
        Returns:
            Trend analysis with recommendation
        """
        if len(historical_data) < 7:
            return {
                'trending': False,
                'reason': 'Insufficient historical data',
                'confidence': 0.0
            }
        
        # Extract counts
        dates = [d['date'] for d in historical_data]
        counts = [d['count'] for d in historical_data]
        
        # Calculate trend
        trend = self._calculate_trend(counts)
        
        # Calculate recent vs historical ratio
        recent_avg = np.mean(counts[-7:])   # Last 7 days
        historical_avg = np.mean(counts[:-7]) if len(counts) > 7 else recent_avg
        
        ratio = recent_avg / historical_avg if historical_avg > 0 else 1.0
        
        # Determine if trending up
        is_trending = (trend > 0.1 and ratio > 1.5)  # >50% increase
        
        # Severity assessment
        if ratio > 3.0:
            severity = 'SEVERE'
        elif ratio > 2.0:
            severity = 'HIGH'
        elif ratio > 1.5:
            severity = 'MODERATE'
        else:
            severity = 'LOW'
        
        return {
            'trending': is_trending,
            'trend_direction': 'UP' if trend > 0 else 'DOWN',
            'trend_strength': abs(trend),
            'recent_vs_historical_ratio': round(ratio, 2),
            'severity': severity,
            'recent_average': round(recent_avg, 1),
            'historical_average': round(historical_avg, 1),
            'confidence': min(1.0, abs(trend) * ratio)
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate trend using linear regression
        
        Returns slope (positive = upward trend)
        """
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Linear regression
        slope, _ = np.polyfit(x, y, 1)
        
        # Normalize by mean
        mean_value = np.mean(y)
        if mean_value > 0:
            normalized_slope = slope / mean_value
        else:
            normalized_slope = 0.0
        
        return normalized_slope


class PreemptiveSafetyEngine:
    """
    Main engine for pre-emptive safety readiness
    
    Monitors signals and adjusts system configuration proactively
    """
    
    def __init__(self):
        self.current_level = ReadinessLevel.NORMAL
        self.current_profile = ReadinessProfile.get_profile(ReadinessLevel.NORMAL)
        self.trend_analyzer = SignalTrendAnalyzer()
        self.readiness_history = []
        self.monitored_signals = {}
    
    def monitor_signal(
        self,
        drug: str,
        event: str,
        prr: float,
        case_count: int,
        temporal_data: List[Dict]
    ):
        """
        Monitor a specific drug-event signal
        
        Determines if readiness should be elevated
        """
        signal_key = f"{drug}_{event}"
        
        # Analyze trend
        trend_analysis = self.trend_analyzer.analyze_trend(temporal_data)
        
        # Determine recommended readiness level
        recommended_level = self._calculate_recommended_level(
            prr, case_count, trend_analysis
        )
        
        # Store monitoring data
        self.monitored_signals[signal_key] = {
            'drug': drug,
            'event': event,
            'prr': prr,
            'case_count': case_count,
            'trend_analysis': trend_analysis,
            'recommended_level': recommended_level,
            'last_checked': datetime.utcnow().isoformat()
        }
        
        # Update system readiness if needed
        if recommended_level.value != self.current_level.value:
            self._escalate_readiness(recommended_level, signal_key, trend_analysis)
    
    def _calculate_recommended_level(
        self,
        prr: float,
        case_count: int,
        trend_analysis: Dict
    ) -> ReadinessLevel:
        """
        Calculate recommended readiness level based on signal characteristics
        """
        score = 0
        
        # PRR factor
        if prr >= 8.0:
            score += 4
        elif prr >= 4.0:
            score += 3
        elif prr >= 2.0:
            score += 2
        
        # Case count factor
        if case_count >= 50:
            score += 3
        elif case_count >= 20:
            score += 2
        elif case_count >= 10:
            score += 1
        
        # Trend factor
        if trend_analysis['trending']:
            severity = trend_analysis['severity']
            if severity == 'SEVERE':
                score += 4
            elif severity == 'HIGH':
                score += 3
            elif severity == 'MODERATE':
                score += 2
        
        # Map score to level
        if score >= 9:
            return ReadinessLevel.CRITICAL
        elif score >= 6:
            return ReadinessLevel.HIGH
        elif score >= 3:
            return ReadinessLevel.ELEVATED
        else:
            return ReadinessLevel.NORMAL
    
    def _escalate_readiness(
        self,
        new_level: ReadinessLevel,
        trigger_signal: str,
        trend_data: Dict
    ):
        """
        Escalate system to new readiness level
        """
        old_level = self.current_level
        
        # Update level
        self.current_level = new_level
        self.current_profile = ReadinessProfile.get_profile(new_level)
        
        # Record in history
        self.readiness_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'old_level': old_level.value,
            'new_level': new_level.value,
            'trigger_signal': trigger_signal,
            'trend_data': trend_data,
            'reason': self._generate_escalation_reason(new_level, trend_data)
        })
        
        # Log escalation
        print(f"\n🚨 READINESS ESCALATION")
        print(f"   From: {old_level.value.upper()}")
        print(f"   To: {new_level.value.upper()}")
        print(f"   Trigger: {trigger_signal}")
        print(f"   Reason: {self.readiness_history[-1]['reason']}")
    
    def _generate_escalation_reason(
        self,
        level: ReadinessLevel,
        trend_data: Dict
    ) -> str:
        """Generate human-readable escalation reason"""
        
        severity = trend_data.get('severity', 'UNKNOWN')
        ratio = trend_data.get('recent_vs_historical_ratio', 1.0)
        
        if level == ReadinessLevel.CRITICAL:
            return f"CRITICAL: Signal intensity {ratio:.1f}x higher than baseline. Immediate action required."
        elif level == ReadinessLevel.HIGH:
            return f"HIGH: {severity} trend detected. Proactive measures activated."
        elif level == ReadinessLevel.ELEVATED:
            return f"ELEVATED: Increasing signal activity. Enhanced monitoring enabled."
        else:
            return "Signal within normal parameters."
    
    def get_current_configuration(self) -> Dict[str, Any]:
        """
        Get current system configuration based on readiness level
        """
        return {
            'readiness_level': self.current_level.value,
            'configuration': self.current_profile,
            'active_since': self.readiness_history[-1]['timestamp'] if self.readiness_history else 'startup',
            'monitored_signals': len(self.monitored_signals),
            'high_priority_signals': sum(
                1 for s in self.monitored_signals.values()
                if s['recommended_level'] in [ReadinessLevel.HIGH, ReadinessLevel.CRITICAL]
            )
        }
    
    def apply_to_case(
        self,
        case_data: Dict
    ) -> Dict[str, Any]:
        """
        Apply current readiness profile to a case
        
        Returns adjusted configuration for this case
        """
        # Check if case matches any monitored signals
        case_drug = case_data.get('suspect_drug', '').upper()
        case_event = case_data.get('adverse_event', '').upper()
        
        matching_signals = []
        for signal_key, signal_data in self.monitored_signals.items():
            if (signal_data['drug'].upper() in case_drug and
                signal_data['event'].upper() in case_event):
                matching_signals.append(signal_data)
        
        # Use highest readiness level if multiple matches
        if matching_signals:
            highest_level = max(
                (s['recommended_level'] for s in matching_signals),
                key=lambda x: list(ReadinessLevel).index(x)
            )
            profile = ReadinessProfile.get_profile(highest_level)
        else:
            profile = self.current_profile.copy()
        
        return {
            'case_specific_config': profile,
            'readiness_level': self.current_level.value,
            'matching_signals': len(matching_signals),
            'signal_triggered': len(matching_signals) > 0,
            'adjustments_applied': [
                f"Confidence threshold: {profile['confidence_threshold']:.0%}",
                f"Priority channel: {profile['priority_channel']}",
                f"Response timeout: {profile['response_timeout_hours']}h",
                f"Auto-escalate: {profile.get('auto_escalate', False)}"
            ]
        }
    
    def get_readiness_dashboard(self) -> Dict[str, Any]:
        """
        Generate dashboard data for monitoring
        """
        return {
            'current_level': self.current_level.value,
            'current_config': self.current_profile,
            'monitored_signals_count': len(self.monitored_signals),
            'recent_escalations': self.readiness_history[-5:] if self.readiness_history else [],
            'active_high_priority': [
                {
                    'signal': f"{s['drug']} + {s['event']}",
                    'prr': s['prr'],
                    'cases': s['case_count'],
                    'level': s['recommended_level'].value
                }
                for s in self.monitored_signals.values()
                if s['recommended_level'] in [ReadinessLevel.HIGH, ReadinessLevel.CRITICAL]
            ],
            'system_adjustments': {
                'confidence_threshold': f"{self.current_profile['confidence_threshold']:.0%}",
                'max_iterations': self.current_profile['max_iterations'],
                'priority_channel': self.current_profile['priority_channel'],
                'auto_escalate': self.current_profile.get('auto_escalate', False)
            }
        }
    
    def reset_to_normal(self, reason: str = "Manual reset"):
        """Reset system to normal readiness"""
        if self.current_level != ReadinessLevel.NORMAL:
            self._escalate_readiness(
                ReadinessLevel.NORMAL,
                reason,
                {'severity': 'RESOLVED'}
            )


# Convenience functions
def monitor_and_adjust(drug: str, event: str, prr: float, cases: int, temporal: List[Dict], engine: PreemptiveSafetyEngine):
    """Quick monitoring"""
    engine.monitor_signal(drug, event, prr, cases, temporal)
    return engine.get_current_configuration()


def get_case_config(case_data: Dict, engine: PreemptiveSafetyEngine) -> Dict:
    """Quick case configuration"""
    return engine.apply_to_case(case_data)
