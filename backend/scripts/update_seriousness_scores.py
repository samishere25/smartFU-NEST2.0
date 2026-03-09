"""
Update seriousness scores for all cases based on adverse events keywords
"""
import sys
from pathlib import Path
import random

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.base import Base  # Import Base first
from app.models.followup import FollowUpAttempt  # Import dependencies first
from app.models.case import AECase

# Keywords indicating serious adverse events
SERIOUS_KEYWORDS = {
    'death': 1.0,
    'died': 1.0,
    'fatal': 1.0,
    'life threatening': 0.95,
    'life-threatening': 0.95,
    'hospitalization': 0.85,
    'hospitalisation': 0.85,
    'hospitalized': 0.85,
    'disability': 0.8,
    'disabled': 0.8,
    'anaphylaxis': 0.9,
    'anaphylactic': 0.9,
    'cardiac arrest': 0.95,
    'respiratory failure': 0.9,
    'renal failure': 0.85,
    'liver failure': 0.85,
    'stroke': 0.85,
    'seizure': 0.75,
    'coma': 0.9,
    'cancer': 0.85,
    'malignancy': 0.85,
    'hemorrhage': 0.8,
    'bleeding': 0.7,
    'sepsis': 0.9,
    'shock': 0.85,
}

MODERATE_KEYWORDS = {
    'pain': 0.4,
    'nausea': 0.3,
    'vomiting': 0.35,
    'diarrhea': 0.3,
    'fever': 0.45,
    'rash': 0.3,
    'headache': 0.25,
    'dizziness': 0.3,
    'fatigue': 0.25,
    'weakness': 0.3,
}

def calculate_seriousness_score(adverse_event: str, event_outcome: str = None) -> float:
    """Calculate seriousness score based on adverse event text"""
    if not adverse_event:
        return 0.3  # Default moderate score
    
    event_lower = adverse_event.lower()
    
    # Check for serious keywords
    max_score = 0.0
    for keyword, score in SERIOUS_KEYWORDS.items():
        if keyword in event_lower:
            max_score = max(max_score, score)
    
    # If no serious keywords found, check moderate
    if max_score == 0.0:
        for keyword, score in MODERATE_KEYWORDS.items():
            if keyword in event_lower:
                max_score = max(max_score, score)
    
    # If still no match, assign based on length/severity indicators
    if max_score == 0.0:
        if any(word in event_lower for word in ['severe', 'serious', 'critical', 'acute']):
            max_score = 0.6
        else:
            max_score = random.uniform(0.3, 0.5)  # Random moderate score
    
    # Boost score if outcome is serious
    if event_outcome:
        outcome_lower = event_outcome.lower()
        if any(word in outcome_lower for word in ['death', 'died', 'fatal', 'hospitalization']):
            max_score = max(max_score, 0.85)
    
    return round(max_score, 2)

def update_all_seriousness_scores():
    """Update seriousness scores for all cases"""
    
    print("\n" + "="*60)
    print("UPDATING SERIOUSNESS SCORES")
    print("="*60 + "\n")
    
    db = SessionLocal()
    
    try:
        # Get all cases
        cases = db.query(AECase).all()
        print(f"Found {len(cases)} cases to update\n")
        
        updated_count = 0
        
        for case in cases:
            # Calculate seriousness score
            score = calculate_seriousness_score(
                case.adverse_event,
                case.event_outcome
            )
            
            # Update case
            case.seriousness_score = score
            case.is_serious = score >= 0.7
            
            # Set risk level based on score
            if score >= 0.8:
                case.risk_level = "CRITICAL"
            elif score >= 0.6:
                case.risk_level = "HIGH"
            elif score >= 0.4:
                case.risk_level = "MEDIUM"
            else:
                case.risk_level = "LOW"
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"Updated {updated_count} cases...")
                db.commit()
        
        # Final commit
        db.commit()
        
        print(f"\n✅ Successfully updated {updated_count} cases")
        
        # Show distribution
        critical = db.query(AECase).filter(AECase.seriousness_score >= 0.8).count()
        high = db.query(AECase).filter(AECase.seriousness_score >= 0.6, AECase.seriousness_score < 0.8).count()
        medium = db.query(AECase).filter(AECase.seriousness_score >= 0.4, AECase.seriousness_score < 0.6).count()
        low = db.query(AECase).filter(AECase.seriousness_score < 0.4).count()
        
        print("\nSeriousness Distribution:")
        print(f"  CRITICAL (≥80%): {critical}")
        print(f"  HIGH (60-79%):   {high}")
        print(f"  MEDIUM (40-59%): {medium}")
        print(f"  LOW (<40%):      {low}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_all_seriousness_scores()
