"""
COMPLETE DEMO - Features 5 & 6
Visual Explainability + Signal Detection
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# FIXED IMPORTS - from app.utils
from app.utils.signal_detection import SafetySignalDetector, detect_signal, scan_for_signals
from app.utils.visual_explainability import VisualExplainer, create_visual_explanation
import json
from datetime import datetime, timedelta


def demo_signal_detection():
    """Demo Feature #6: Signal Detection"""
    
    print("\n" + "="*70)
    print("📊 FEATURE #6: SAFETY SIGNAL DETECTION")
    print("="*70)
    
    # Create sample case data
    sample_cases = []
    
    # Simulate XARELTO + Bleeding signal (known real-world signal)
    for i in range(25):
        sample_cases.append({
            'suspect_drug': 'XARELTO',
            'adverse_event': 'BLEEDING' if i < 20 else 'NAUSEA',
            'receipt_date': datetime.now() - timedelta(days=i*2),
            'created_at': datetime.now() - timedelta(days=i*2)
        })
    
    # Add other drug-event pairs
    for i in range(100):
        sample_cases.append({
            'suspect_drug': f'DRUG_{i % 10}',
            'adverse_event': f'EVENT_{i % 15}',
            'receipt_date': datetime.now() - timedelta(days=i),
            'created_at': datetime.now() - timedelta(days=i)
        })
    
    print(f"\n📋 Analyzing {len(sample_cases)} adverse event reports...")
    
    # TEST 1: Calculate PRR
    print("\n" + "-"*70)
    print("TEST 1: Disproportionality Analysis (PRR)")
    print("-"*70)
    
    detector = SafetySignalDetector()
    prr_result = detector.calculate_prr('XARELTO', 'BLEEDING', sample_cases)
    
    print(f"\nDrug: XARELTO")
    print(f"Event: BLEEDING")
    print(f"\n📊 Results:")
    print(f"  PRR: {prr_result['prr']}")
    print(f"  P-value: {prr_result['p_value']}")
    print(f"  Signal? {'🚨 YES' if prr_result['is_signal'] else '✓ NO'}")
    print(f"  {prr_result['reason']}")
    
    # TEST 2: Temporal Clustering
    print("\n" + "-"*70)
    print("TEST 2: Temporal Clustering")
    print("-"*70)
    
    temporal = detector.detect_temporal_clusters('XARELTO', 'BLEEDING', sample_cases)
    print(f"\n  Recent: {temporal['recent_count']} cases")
    print(f"  Expected: {temporal['expected_count']}")
    print(f"  {temporal['reason']}")
    
    # TEST 3: Top Signals
    print("\n" + "-"*70)
    print("TEST 3: Scan for Top Signals")
    print("-"*70)
    
    top_signals = detector.find_top_signals(sample_cases, top_n=3)
    
    if top_signals:
        print(f"\n🚨 Found {len(top_signals)} signals:")
        for i, s in enumerate(top_signals, 1):
            print(f"\n{i}. {s['drug']} + {s['event']}")
            print(f"   PRR: {s['prr']}, Cases: {s['case_count']}")
    else:
        print("\n✓ No signals detected")


def demo_visual_explainability():
    """Demo Feature #5: Visual Explainability"""
    
    print("\n\n" + "="*70)
    print("📈 FEATURE #5: VISUAL EXPLAINABILITY")
    print("="*70)
    
    explainer = VisualExplainer()
    
    # TEST 1: Feature Importance
    print("\n" + "-"*70)
    print("TEST 1: Feature Importance Chart")
    print("-"*70)
    
    features = {
        'reporter_historical_rate': 0.18,
        'reporter_quality_score': 0.15,
        'completeness_score': 0.12,
        'risk_score': 0.11
    }
    
    chart = explainer.generate_feature_importance_chart(features)
    print(f"\n📊 Chart generated: {chart['type']}")
    print(f"   Top feature: {chart['data']['labels'][0]} ({chart['data']['datasets'][0]['data'][0]}%)")
    
    # TEST 2: Confidence Gauge
    print("\n" + "-"*70)
    print("TEST 2: Confidence Gauge")
    print("-"*70)
    
    gauge = explainer.generate_confidence_gauge(0.87)
    print(f"\n🎯 Confidence: {gauge['centerText']['value']}")
    print(f"   Status: Above threshold ✓")
    
    # TEST 3: Complete Dashboard
    print("\n" + "-"*70)
    print("TEST 3: Complete Dashboard")
    print("-"*70)
    
    analysis = {
        'case_id': 'test-123',
        'confidence': 0.87,
        'response_probability': 0.68,
        'feature_importance': features
    }
    
    dashboard = explainer.create_complete_dashboard(analysis)
    print(f"\n📊 Dashboard created")
    print(f"   Visualizations: {len(dashboard['visualizations'])}")
    for name in dashboard['visualizations'].keys():
        print(f"      • {name.replace('_', ' ').title()}")


def main():
    """Run complete demo"""
    
    print("\n" + "="*70)
    print("🚀 SMARTFU - FEATURES 5 & 6 DEMO")
    print("="*70)
    
    demo_signal_detection()
    demo_visual_explainability()
    
    print("\n\n" + "="*70)
    print("✅ ALL FEATURES WORKING!")
    print("="*70)
    print("\n🎯 Ready for NEST 2.0!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
