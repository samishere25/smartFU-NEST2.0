"""
Load FAERS data into database
"""
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.case import AECase
from app.models.followup import FollowUpAttempt, FollowUpDecision, CaseConfidenceHistory, AdaptiveLoopSession
from app.core.config import settings

def load_faers_dataset():
    """Load FAERS dataset from CSV"""
    
    print("\n" + "="*60)
    print("SMARTFU - DATA LOADER")
    print("="*60 + "\n")
    
    # Find CSV file
    csv_path = Path(__file__).parent.parent / "data.csv"
    
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found at {csv_path}")
        return
    
    print(f"📁 Found CSV file: {csv_path.name}")
    
    # Load data
    df = pd.read_csv(csv_path)
    print(f"Loading data from: {csv_path}")
    print(f"Found {len(df)} records")
    
    # Remove duplicates based on primaryid
    df = df.drop_duplicates(subset=['primaryid'], keep='first')
    print(f"After removing duplicates: {len(df)} unique records")
    
    db = SessionLocal()
    
    created_count = 0
    failed_count = 0
    errors = []
    
    try:
        for idx, row in df.iterrows():
            try:
                # Check if case already exists
                existing = db.query(AECase).filter(
                    AECase.primaryid == int(row['primaryid'])
                ).first()
                
                if existing:
                    continue
                
                # Create case
                case = AECase(
                    case_id=uuid.uuid4(),
                    primaryid=int(row['primaryid']),
                    receipt_date=datetime.utcnow(),
                    patient_age=int(row['age']) if pd.notna(row['age']) else None,
                    patient_sex=str(row['sex']) if pd.notna(row['sex']) else None,
                    suspect_drug=str(row['suspect_drug']),
                    drug_route=str(row['route']) if pd.notna(row['route']) else None,
                    drug_dose=str(row['dose_vbm']) if pd.notna(row['dose_vbm']) else None,
                    adverse_event=str(row['adverse_event']),
                    event_date=None,  # Parse event_dt if needed
                    reporter_type=str(row['occp_cod']) if pd.notna(row['occp_cod']) else None,
                    seriousness_score=0.0,
                    data_completeness_score=0.0,
                    is_serious=False,
                    requires_followup=True
                )
                
                db.add(case)
                db.commit()
                created_count += 1
                
                if created_count % 100 == 0:
                    print(f"Loaded {created_count} cases...")
                
            except Exception as e:
                failed_count += 1
                if len(errors) < 5:
                    errors.append(f"Row {idx}: {str(e)}")
                db.rollback()
                continue
        
        print("\nResults:")
        print(f"  Total: {len(df)}")
        print(f"  Created: {created_count}")
        print(f"  Failed: {failed_count}")
        
        if errors:
            print("\nFirst 5 errors:")
            for error in errors:
                print(f"  {error}")
        
        print("\n" + "="*60)
        print("✅ DATA LOADING COMPLETE!")
        print("="*60 + "\n")
        print(f"Successfully loaded {created_count} cases")
        if failed_count > 0:
            print(f"⚠️  {failed_count} records failed")
        
    finally:
        db.close()


if __name__ == "__main__":
    load_faers_dataset()
