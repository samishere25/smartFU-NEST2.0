"""
Safety Signal Detection System
Detects patterns and clusters across all adverse event cases
Identifies potential drug safety issues early
"""

from typing import Dict, List, Tuple, Any
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import math


class SafetySignalDetector:
    """
    Detects safety signals by analyzing patterns across all cases
    
    Methods:
    - Drug-event pair analysis (disproportionality)
    - Temporal clustering (sudden increases)
    - Severity pattern detection
    - Statistical significance testing
    """
    
    def __init__(self, significance_threshold: float = 0.05):
        self.significance_threshold = significance_threshold
        self.min_cases_for_signal = 3  # Minimum cases to detect signal
    
    def calculate_prr(
        self,
        drug: str,
        event: str,
        all_cases: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate Proportional Reporting Ratio (PRR)
        
        PRR is the standard method for pharmacovigilance signal detection
        
        PRR = (a/b) / (c/d)
        where:
        a = reports with drug AND event
        b = reports with drug but NOT event
        c = reports with event but NOT drug
        d = reports with neither drug nor event
        
        PRR > 2.0 with chi-square p < 0.05 = potential signal
        """
        # Build contingency table
        a = 0  # Drug + Event
        b = 0  # Drug + Not Event
        c = 0  # Not Drug + Event
        d = 0  # Not Drug + Not Event
        
        for case in all_cases:
            case_drug = case.get('suspect_drug', '').upper()
            case_event = case.get('adverse_event', '').upper()
            
            has_drug = drug.upper() in case_drug
            has_event = event.upper() in case_event
            
            if has_drug and has_event:
                a += 1
            elif has_drug and not has_event:
                b += 1
            elif not has_drug and has_event:
                c += 1
            else:
                d += 1
        
        # Calculate PRR
        if b == 0 or c == 0 or d == 0:
            return {
                'prr': 0.0,
                'chi_square': 0.0,
                'p_value': 1.0,
                'is_signal': False,
                'a': a, 'b': b, 'c': c, 'd': d,
                'reason': 'Insufficient data for calculation'
            }
        
        prr = (a / b) / (c / d)
        
        # Calculate chi-square statistic
        n = a + b + c + d
        expected_a = ((a + b) * (a + c)) / n
        
        if expected_a == 0:
            chi_square = 0.0
        else:
            chi_square = ((a - expected_a) ** 2) / expected_a
        
        # Approximate p-value from chi-square (1 degree of freedom)
        # Using simplified approximation
        p_value = math.exp(-chi_square / 2)
        
        # Signal criteria: PRR ≥ 2.0 AND p < 0.05 AND a ≥ 3
        is_signal = (prr >= 2.0 and p_value < self.significance_threshold and a >= self.min_cases_for_signal)
        
        return {
            'prr': round(prr, 2),
            'chi_square': round(chi_square, 2),
            'p_value': round(p_value, 4),
            'is_signal': is_signal,
            'confidence': 'HIGH' if prr > 4.0 else 'MEDIUM' if prr > 2.0 else 'LOW',
            'a': a,
            'b': b,
            'c': c,
            'd': d,
            'total_cases': n,
            'reason': self._interpret_prr(prr, p_value, a)
        }
    
    def _interpret_prr(self, prr: float, p_value: float, count: int) -> str:
        """Human-readable interpretation"""
        if count < self.min_cases_for_signal:
            return f"Too few cases ({count}) for reliable signal"
        elif prr >= 4.0 and p_value < 0.01:
            return f"STRONG SIGNAL: {prr:.1f}x higher than expected (p={p_value:.4f})"
        elif prr >= 2.0 and p_value < 0.05:
            return f"POTENTIAL SIGNAL: {prr:.1f}x higher than expected (p={p_value:.4f})"
        elif prr >= 1.5:
            return f"WEAK SIGNAL: {prr:.1f}x higher than expected (not statistically significant)"
        else:
            return f"NO SIGNAL: Reporting rate is expected ({prr:.1f}x)"
    
    def detect_temporal_clusters(
        self,
        drug: str,
        event: str,
        all_cases: List[Dict],
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect sudden increases in reporting (temporal clustering)
        
        Identifies if there's a recent spike in reports
        """
        # Filter relevant cases
        relevant_cases = []
        for case in all_cases:
            case_drug = case.get('suspect_drug', '').upper()
            case_event = case.get('adverse_event', '').upper()
            
            if drug.upper() in case_drug and event.upper() in case_event:
                receipt_date = case.get('receipt_date') or case.get('created_at')
                if receipt_date:
                    relevant_cases.append({
                        'date': receipt_date if isinstance(receipt_date, datetime) else datetime.now(),
                        'case': case
                    })
        
        if len(relevant_cases) < 3:
            return {
                'is_cluster': False,
                'reason': 'Insufficient cases for temporal analysis',
                'recent_count': len(relevant_cases)
            }
        
        # Sort by date
        relevant_cases.sort(key=lambda x: x['date'])
        
        # Calculate recent vs historical rate
        now = datetime.now()
        recent_cutoff = now - timedelta(days=window_days)
        
        recent_cases = [c for c in relevant_cases if c['date'] >= recent_cutoff]
        historical_cases = [c for c in relevant_cases if c['date'] < recent_cutoff]
        
        recent_count = len(recent_cases)
        historical_count = len(historical_cases)
        
        if historical_count == 0:
            return {
                'is_cluster': recent_count >= 3,
                'reason': f'All {recent_count} cases are recent (no historical baseline)',
                'recent_count': recent_count,
                'expected_count': 0
            }
        
        # Calculate expected rate
        total_days = (now - relevant_cases[0]['date']).days
        if total_days == 0:
            total_days = 1
        
        historical_rate = historical_count / max(1, total_days - window_days)
        expected_recent = historical_rate * window_days
        
        # Is recent count significantly higher?
        ratio = recent_count / max(1, expected_recent)
        
        is_cluster = (recent_count >= 3 and ratio >= 2.0)
        
        return {
            'is_cluster': is_cluster,
            'recent_count': recent_count,
            'expected_count': round(expected_recent, 1),
            'ratio': round(ratio, 2),
            'window_days': window_days,
            'confidence': 'HIGH' if ratio > 4.0 else 'MEDIUM' if ratio > 2.0 else 'LOW',
            'reason': f"Recent rate {ratio:.1f}x higher than expected" if is_cluster else "No unusual clustering"
        }
    
    def analyze_severity_pattern(
        self,
        drug: str,
        all_cases: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze if a drug has unusual severity patterns
        
        Checks if serious outcomes are disproportionately high
        """
        drug_cases = []
        other_cases = []
        
        for case in all_cases:
            case_drug = case.get('suspect_drug', '').upper()
            event = case.get('adverse_event', '').lower()
            
            # Determine if serious
            is_serious = any(word in event for word in ['death', 'died', 'fatal', 'hospitalization', 'disability'])
            
            if drug.upper() in case_drug:
                drug_cases.append({'serious': is_serious})
            else:
                other_cases.append({'serious': is_serious})
        
        if len(drug_cases) < 3:
            return {
                'is_concerning': False,
                'reason': 'Insufficient cases for severity analysis'
            }
        
        # Calculate serious percentages
        drug_serious_pct = sum(1 for c in drug_cases if c['serious']) / len(drug_cases)
        other_serious_pct = sum(1 for c in other_cases if c['serious']) / len(other_cases) if other_cases else 0.2
        
        # Is drug's serious percentage significantly higher?
        ratio = drug_serious_pct / max(0.01, other_serious_pct)
        
        is_concerning = (drug_serious_pct > 0.5 and ratio > 1.5)
        
        return {
            'is_concerning': is_concerning,
            'drug_serious_rate': round(drug_serious_pct, 2),
            'baseline_serious_rate': round(other_serious_pct, 2),
            'ratio': round(ratio, 2),
            'drug_case_count': len(drug_cases),
            'reason': f"Serious outcomes {ratio:.1f}x higher than baseline" if is_concerning else "Severity pattern is expected"
        }
    
    def find_top_signals(
        self,
        all_cases: List[Dict],
        top_n: int = 10
    ) -> List[Dict]:
        """
        Scan all drug-event pairs and find top signals
        
        Returns ranked list of potential safety signals
        """
        # Count drug-event pairs
        pairs = defaultdict(int)
        
        for case in all_cases:
            drug = case.get('suspect_drug', '').upper()
            event = case.get('adverse_event', '').upper()
            
            if drug and event:
                # Take first word of each (simplification)
                drug_name = drug.split()[0] if drug else 'UNKNOWN'
                event_name = event.split()[0] if event else 'UNKNOWN'
                
                pairs[(drug_name, event_name)] += 1
        
        # Filter to pairs with enough cases
        candidates = [(d, e, count) for (d, e), count in pairs.items() if count >= self.min_cases_for_signal]
        
        # Calculate PRR for each
        signals = []
        
        for drug, event, count in candidates:
            prr_result = self.calculate_prr(drug, event, all_cases)
            
            if prr_result['is_signal']:
                signals.append({
                    'drug': drug,
                    'event': event,
                    'case_count': count,
                    'prr': prr_result['prr'],
                    'p_value': prr_result['p_value'],
                    'confidence': prr_result['confidence'],
                    'reason': prr_result['reason']
                })
        
        # Sort by PRR (highest first)
        signals.sort(key=lambda x: x['prr'], reverse=True)
        
        return signals[:top_n]
    
    def generate_alert(
        self,
        drug: str,
        event: str,
        prr_result: Dict,
        temporal_result: Dict,
        severity_result: Dict
    ) -> Dict[str, Any]:
        """
        Generate comprehensive alert for a signal
        
        Returns alert with priority and recommended actions
        """
        # Calculate priority
        priority_score = 0
        
        if prr_result['is_signal']:
            priority_score += 5
            if prr_result['prr'] > 4.0:
                priority_score += 3
        
        if temporal_result['is_cluster']:
            priority_score += 4
        
        if severity_result['is_concerning']:
            priority_score += 5
        
        # Determine priority level
        if priority_score >= 10:
            priority = 'CRITICAL'
            action = 'IMMEDIATE_REVIEW_REQUIRED'
        elif priority_score >= 7:
            priority = 'HIGH'
            action = 'EXPEDITED_REVIEW'
        elif priority_score >= 4:
            priority = 'MEDIUM'
            action = 'ROUTINE_MONITORING'
        else:
            priority = 'LOW'
            action = 'CONTINUED_SURVEILLANCE'
        
        return {
            'drug': drug,
            'event': event,
            'priority': priority,
            'priority_score': priority_score,
            'recommended_action': action,
            'disproportionality': prr_result,
            'temporal_clustering': temporal_result,
            'severity_pattern': severity_result,
            'alert_generated_at': datetime.now().isoformat(),
            'requires_notification': priority in ['CRITICAL', 'HIGH']
        }


# Convenience functions
def detect_signal(drug: str, event: str, all_cases: List[Dict]) -> Dict:
    """Quick signal detection"""
    detector = SafetySignalDetector()
    prr = detector.calculate_prr(drug, event, all_cases)
    temporal = detector.detect_temporal_clusters(drug, event, all_cases)
    severity = detector.analyze_severity_pattern(drug, all_cases)
    
    return detector.generate_alert(drug, event, prr, temporal, severity)


def scan_for_signals(all_cases: List[Dict], top_n: int = 10) -> List[Dict]:
    """Scan database for top signals"""
    detector = SafetySignalDetector()
    return detector.find_top_signals(all_cases, top_n)
