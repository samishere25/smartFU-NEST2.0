"""
Create sample safety signals for testing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.signal import SafetySignal
from datetime import datetime, timedelta
import uuid

def create_sample_signals():
    db = SessionLocal()
    
    # Clear existing signals
    db.query(SafetySignal).delete()
    
    # Sample signals with varying severity levels
    sample_signals = [
        {
            'drug_name': 'Aspirin',
            'adverse_event': 'Gastrointestinal Bleeding',
            'signal_type': 'EMERGING',
            'case_count': 47,
            'reporting_rate': 0.023,
            'proportional_reporting_ratio': 8.7,
            'trend': 'UP',
            'signal_strength': 'STRONG',
            'clinical_significance': 'High risk of GI bleeding in elderly patients, especially with concurrent NSAID use',
            'signal_status': 'UNDER_REVIEW',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=5)
        },
        {
            'drug_name': 'Warfarin',
            'adverse_event': 'Intracranial Hemorrhage',
            'signal_type': 'CONFIRMED',
            'case_count': 89,
            'reporting_rate': 0.041,
            'proportional_reporting_ratio': 12.3,
            'trend': 'UP',
            'signal_strength': 'STRONG',
            'clinical_significance': 'Critical risk in patients with INR >3.0, requires immediate intervention',
            'signal_status': 'ESCALATED',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=10)
        },
        {
            'drug_name': 'Metformin',
            'adverse_event': 'Lactic Acidosis',
            'signal_type': 'EMERGING',
            'case_count': 34,
            'reporting_rate': 0.015,
            'proportional_reporting_ratio': 6.2,
            'trend': 'STABLE',
            'signal_strength': 'MODERATE',
            'clinical_significance': 'Rare but serious complication, primarily in patients with renal impairment',
            'signal_status': 'NEW',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=3)
        },
        {
            'drug_name': 'Ciprofloxacin',
            'adverse_event': 'Tendon Rupture',
            'signal_type': 'CONFIRMED',
            'case_count': 23,
            'reporting_rate': 0.011,
            'proportional_reporting_ratio': 5.4,
            'trend': 'DOWN',
            'signal_strength': 'MODERATE',
            'clinical_significance': 'Risk increases with age >60 and concurrent corticosteroid use',
            'signal_status': 'UNDER_REVIEW',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=15)
        },
        {
            'drug_name': 'Amiodarone',
            'adverse_event': 'Pulmonary Toxicity',
            'signal_type': 'EMERGING',
            'case_count': 56,
            'reporting_rate': 0.028,
            'proportional_reporting_ratio': 9.1,
            'trend': 'UP',
            'signal_strength': 'STRONG',
            'clinical_significance': 'Potentially life-threatening, requires chest imaging and pulmonary function monitoring',
            'signal_status': 'NEW',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=2)
        },
        {
            'drug_name': 'Atorvastatin',
            'adverse_event': 'Rhabdomyolysis',
            'signal_type': 'EMERGING',
            'case_count': 18,
            'reporting_rate': 0.008,
            'proportional_reporting_ratio': 3.7,
            'trend': 'STABLE',
            'signal_strength': 'MODERATE',
            'clinical_significance': 'Risk elevated with high doses and drug interactions (e.g., gemfibrozil)',
            'signal_status': 'NEW',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=7)
        },
        {
            'drug_name': 'Isotretinoin',
            'adverse_event': 'Depression/Suicidal Ideation',
            'signal_type': 'CONFIRMED',
            'case_count': 41,
            'reporting_rate': 0.019,
            'proportional_reporting_ratio': 4.8,
            'trend': 'STABLE',
            'signal_strength': 'MODERATE',
            'clinical_significance': 'Psychiatric monitoring required, especially in adolescents',
            'signal_status': 'UNDER_REVIEW',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=12)
        },
        {
            'drug_name': 'Clozapine',
            'adverse_event': 'Agranulocytosis',
            'signal_type': 'CONFIRMED',
            'case_count': 67,
            'reporting_rate': 0.032,
            'proportional_reporting_ratio': 7.9,
            'trend': 'STABLE',
            'signal_strength': 'STRONG',
            'clinical_significance': 'Life-threatening, mandatory weekly blood monitoring for first 6 months',
            'signal_status': 'UNDER_REVIEW',
            'is_active': True,
            'detected_at': datetime.utcnow() - timedelta(days=20)
        }
    ]
    
    # Insert signals
    for signal_data in sample_signals:
        signal = SafetySignal(**signal_data)
        db.add(signal)
    
    db.commit()
    
    # Verify
    count = db.query(SafetySignal).count()
    print(f"✅ Created {count} sample safety signals")
    
    # Show summary
    active_signals = db.query(SafetySignal).filter(SafetySignal.is_active == True).all()
    print(f"\nActive Signals by Status:")
    for status in ['NEW', 'UNDER_REVIEW', 'ESCALATED']:
        count = len([s for s in active_signals if s.signal_status == status])
        print(f"  - {status}: {count}")
    
    print(f"\nSignals by Escalation Level:")
    immediate = len([s for s in active_signals if s.prr >= 8 and s.trend == 'UP'])
    high = len([s for s in active_signals if s.prr >= 5 and s.prr < 8])
    medium = len([s for s in active_signals if s.prr >= 3 and s.prr < 5])
    low = len([s for s in active_signals if s.prr < 3])
    print(f"  - IMMEDIATE: {immediate}")
    print(f"  - HIGH: {high}")
    print(f"  - MEDIUM: {medium}")
    print(f"  - LOW: {low}")
    
    db.close()

if __name__ == "__main__":
    create_sample_signals()
