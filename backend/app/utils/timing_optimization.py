"""
Timing Optimization Module
Predicts best time to send follow-up questions
"""

from datetime import datetime, time, timedelta
from typing import Dict, Tuple
import numpy as np


class TimingOptimizer:
    """
    Optimizes when to send follow-up questions
    Based on reporter type, timezone, and historical response patterns
    """
    
    # Response rates by time of day (based on research)
    TIME_OF_DAY_RATES = {
        'MD': {
            'morning': (time(8, 0), time(11, 0), 1.15),    # 8-11am: +15%
            'midday': (time(11, 0), time(14, 0), 0.85),    # 11am-2pm: -15%
            'afternoon': (time(14, 0), time(17, 0), 1.10), # 2-5pm: +10%
            'evening': (time(17, 0), time(20, 0), 0.70),   # 5-8pm: -30%
            'night': (time(20, 0), time(8, 0), 0.30)       # 8pm-8am: -70%
        },
        'HP': {
            'morning': (time(7, 0), time(10, 0), 1.20),
            'midday': (time(10, 0), time(14, 0), 0.95),
            'afternoon': (time(14, 0), time(16, 0), 1.05),
            'evening': (time(16, 0), time(19, 0), 0.75),
            'night': (time(19, 0), time(7, 0), 0.40)
        },
        'PH': {
            'morning': (time(9, 0), time(12, 0), 1.10),
            'midday': (time(12, 0), time(14, 0), 0.90),
            'afternoon': (time(14, 0), time(18, 0), 1.15),
            'evening': (time(18, 0), time(21, 0), 0.65),
            'night': (time(21, 0), time(9, 0), 0.25)
        },
        'CN': {  # Consumers - more flexible
            'morning': (time(9, 0), time(12, 0), 1.05),
            'midday': (time(12, 0), time(14, 0), 0.95),
            'afternoon': (time(14, 0), time(18, 0), 1.00),
            'evening': (time(18, 0), time(22, 0), 1.20),   # Best time!
            'night': (time(22, 0), time(9, 0), 0.30)
        }
    }
    
    # Response rates by day of week
    DAY_OF_WEEK_RATES = {
        'MD': {0: 1.10, 1: 1.15, 2: 1.15, 3: 1.10, 4: 1.00, 5: 0.60, 6: 0.40},  # Mon-Sun
        'HP': {0: 1.12, 1: 1.15, 2: 1.12, 3: 1.10, 4: 0.95, 5: 0.70, 6: 0.50},
        'PH': {0: 1.15, 1: 1.20, 2: 1.15, 3: 1.10, 4: 1.00, 5: 0.65, 6: 0.45},
        'CN': {0: 0.95, 1: 0.95, 2: 0.95, 3: 0.95, 4: 1.00, 5: 1.15, 6: 1.20}   # Consumers prefer weekends
    }
    
    def get_optimal_send_time(
        self,
        reporter_type: str,
        current_time: datetime = None
    ) -> Dict[str, any]:
        """
        Calculate optimal time to send follow-up
        
        Args:
            reporter_type: Type of reporter (MD, HP, PH, CN, LW)
            current_time: Current datetime (default: now)
        
        Returns:
            dict with optimal_time, delay_hours, multiplier, reasoning
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Get reporter patterns (default to CN if unknown)
        time_patterns = self.TIME_OF_DAY_RATES.get(
            reporter_type, 
            self.TIME_OF_DAY_RATES['CN']
        )
        day_patterns = self.DAY_OF_WEEK_RATES.get(
            reporter_type,
            self.DAY_OF_WEEK_RATES['CN']
        )
        
        # Find best time slot today and tomorrow
        candidates = []
        
        for days_ahead in range(0, 7):  # Check next 7 days
            check_date = current_time + timedelta(days=days_ahead)
            day_of_week = check_date.weekday()
            day_multiplier = day_patterns[day_of_week]
            
            # Skip weekends for professionals (unless urgent)
            if reporter_type in ['MD', 'HP', 'PH'] and day_of_week >= 5:
                continue
            
            # Check each time slot
            for slot_name, (start, end, time_multiplier) in time_patterns.items():
                if slot_name == 'night':
                    continue  # Skip night slots
                
                # Calculate send time (start of slot)
                send_time = check_date.replace(
                    hour=start.hour,
                    minute=start.minute,
                    second=0
                )
                
                # Must be in future
                if send_time <= current_time:
                    continue
                
                # Calculate combined multiplier
                combined_multiplier = day_multiplier * time_multiplier
                
                candidates.append({
                    'send_time': send_time,
                    'slot_name': slot_name,
                    'day_name': send_time.strftime('%A'),
                    'multiplier': combined_multiplier,
                    'delay_hours': (send_time - current_time).total_seconds() / 3600
                })
        
        # Sort by multiplier (best first)
        candidates.sort(key=lambda x: x['multiplier'], reverse=True)
        
        if not candidates:
            # Fallback: send in 1 hour
            fallback_time = current_time + timedelta(hours=1)
            return {
                'optimal_time': fallback_time,
                'delay_hours': 1.0,
                'multiplier': 1.0,
                'reasoning': 'Default: No optimal slot found, sending soon'
            }
        
        # Get best option
        best = candidates[0]
        
        # If best option is >24 hours away, get sooner option
        if best['delay_hours'] > 24:
            for candidate in candidates:
                if candidate['delay_hours'] <= 12:
                    best = candidate
                    break
        
        reasoning = (
            f"Best time: {best['day_name']} {best['slot_name']} "
            f"(+{(best['multiplier']-1)*100:.0f}% response rate)"
        )
        
        return {
            'optimal_time': best['send_time'],
            'delay_hours': round(best['delay_hours'], 1),
            'multiplier': round(best['multiplier'], 2),
            'slot': best['slot_name'],
            'reasoning': reasoning
        }
    
    def calculate_timing_adjusted_probability(
        self,
        base_probability: float,
        reporter_type: str,
        send_time: datetime = None
    ) -> float:
        """
        Adjust response probability based on send timing
        """
        if send_time is None:
            send_time = datetime.now()
        
        timing_info = self.get_optimal_send_time(reporter_type, send_time)
        
        # Adjust probability
        adjusted = base_probability * timing_info['multiplier']
        
        return min(0.95, max(0.10, adjusted))


class ChannelSelector:
    """
    Selects optimal communication channel
    Email, Phone, Portal, SMS
    """
    
    # Channel preferences by reporter type
    CHANNEL_PREFERENCES = {
        'MD': {
            'email': {'preference': 0.70, 'response_rate': 0.68},
            'portal': {'preference': 0.20, 'response_rate': 0.75},
            'phone': {'preference': 0.08, 'response_rate': 0.45},
            'sms': {'preference': 0.02, 'response_rate': 0.30}
        },
        'HP': {
            'email': {'preference': 0.75, 'response_rate': 0.63},
            'portal': {'preference': 0.15, 'response_rate': 0.70},
            'phone': {'preference': 0.08, 'response_rate': 0.50},
            'sms': {'preference': 0.02, 'response_rate': 0.35}
        },
        'PH': {
            'email': {'preference': 0.80, 'response_rate': 0.58},
            'portal': {'preference': 0.12, 'response_rate': 0.65},
            'phone': {'preference': 0.06, 'response_rate': 0.55},
            'sms': {'preference': 0.02, 'response_rate': 0.40}
        },
        'CN': {
            'email': {'preference': 0.50, 'response_rate': 0.35},
            'portal': {'preference': 0.10, 'response_rate': 0.40},
            'phone': {'preference': 0.25, 'response_rate': 0.60},
            'sms': {'preference': 0.15, 'response_rate': 0.45}
        },
        'LW': {
            'email': {'preference': 0.85, 'response_rate': 0.45},
            'portal': {'preference': 0.10, 'response_rate': 0.50},
            'phone': {'preference': 0.03, 'response_rate': 0.40},
            'sms': {'preference': 0.02, 'response_rate': 0.30}
        }
    }
    
    def select_optimal_channel(
        self,
        reporter_type: str,
        urgency: str = 'normal',  # 'low', 'normal', 'high', 'critical'
        complexity: int = 1  # Number of questions
    ) -> Dict[str, any]:
        """
        Select best communication channel
        
        Args:
            reporter_type: Type of reporter
            urgency: How urgent is the follow-up
            complexity: How many questions (simple vs complex)
        
        Returns:
            dict with channel, expected_rate, reasoning
        """
        preferences = self.CHANNEL_PREFERENCES.get(
            reporter_type,
            self.CHANNEL_PREFERENCES['CN']
        )
        
        # Calculate scores for each channel
        scores = {}
        
        for channel, data in preferences.items():
            score = data['response_rate'] * data['preference']
            
            # Adjust for urgency
            if urgency == 'critical':
                if channel == 'phone':
                    score *= 1.5
                elif channel == 'sms':
                    score *= 1.3
            elif urgency == 'high':
                if channel == 'phone':
                    score *= 1.2
            
            # Adjust for complexity
            if complexity > 3:  # Many questions
                if channel == 'email':
                    score *= 1.2  # Better for complex
                elif channel == 'phone':
                    score *= 0.8  # Harder by phone
            
            scores[channel] = score
        
        # Select best
        best_channel = max(scores, key=scores.get)
        expected_rate = preferences[best_channel]['response_rate']
        
        # Reasoning
        reasoning_map = {
            'email': 'Professional, detailed questions',
            'portal': 'Secure, tracked responses',
            'phone': 'Urgent, immediate response needed',
            'sms': 'Quick, simple question'
        }
        
        reasoning = f"{best_channel.title()}: {reasoning_map.get(best_channel, 'Best option')}"
        
        return {
            'channel': best_channel,
            'expected_response_rate': round(expected_rate, 2),
            'urgency': urgency,
            'reasoning': reasoning,
            'all_scores': {k: round(v, 2) for k, v in scores.items()}
        }


# Convenience functions
def get_optimal_timing(reporter_type: str) -> Dict:
    """Quick access to timing optimization"""
    optimizer = TimingOptimizer()
    return optimizer.get_optimal_send_time(reporter_type)


def get_optimal_channel(reporter_type: str, urgency: str = 'normal') -> Dict:
    """Quick access to channel selection"""
    selector = ChannelSelector()
    return selector.select_optimal_channel(reporter_type, urgency)
