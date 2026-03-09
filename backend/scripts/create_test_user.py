"""Create test user for SmartFU"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

print("Creating test user...")

db = SessionLocal()

try:
    # Delete existing user if any
    existing = db.query(User).filter(User.email == "test@example.com").first()
    if existing:
        db.delete(existing)
        db.commit()
        print("✓ Deleted existing user")
    
    # Create new user with CORRECT field names
    user = User()
    user.email = "test@example.com"
    user.username = "testuser"
    user.password_hash = get_password_hash("testpass123")
    user.full_name = "Test User"
    user.is_active = True
    user.role = "admin"
    user.can_approve_high_risk = True
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    print("✅ Test user created successfully!")
    print(f"\nCredentials:")
    print(f"Email: test@example.com")
    print(f"Username: testuser")
    print(f"Password: testpass123")
    print(f"User ID: {user.user_id}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
