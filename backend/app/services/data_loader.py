"""
Data Loading Service
"""

import pandas as pd
from sqlalchemy.orm import Session
from pathlib import Path

from app.services.case_service import CaseService

async def load_faers_dataset(csv_path: str, db: Session):
    """Load FAERS dataset"""
    print(f"Loading data from: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"Found {len(df)} records")
    
    case_service = CaseService(db)
    result = await case_service.bulk_upload_csv(df)
    
    print(f"\nResults:")
    print(f"  Total: {result['total']}")
    print(f"  Created: {result['created']}")
    print(f"  Failed: {result['failed']}")
    
    if result['errors']:
        print(f"\nFirst 5 errors:")
        for error in result['errors'][:5]:
            print(f"  Row {error['row']}: {error['error']}")
    
    return result
