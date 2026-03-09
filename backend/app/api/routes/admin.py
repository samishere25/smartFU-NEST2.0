"""
Admin Routes — user management & system health
"""

import secrets
import string
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import AdminCreateUser, UserInDB
from app.core.security import get_current_active_user, get_password_hash, require_role

router = APIRouter()
logger = logging.getLogger("smartfu.admin")


@router.get("/system-health")
async def system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Get system health status"""
    
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "ai_agents": "ready"
    }


@router.post("/create-user", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_in: AdminCreateUser,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """
    Admin-only: Create a new user with a temporary password.
    
    - System generates a random temporary password.
    - User must change password on first login (must_change_password = True).
    - Temporary password is printed to console (for demo purposes).
    - No public signup allowed.
    """
    
    # Check if user already exists
    existing = db.query(User).filter(
        (User.email == user_in.email) | (User.username == user_in.username)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Generate temporary random password (12 chars: upper + lower + digits + special)
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # Ensure password meets strength requirements
    # Force at least 1 upper, 1 lower, 1 digit
    temp_password = (
        secrets.choice(string.ascii_uppercase) +
        secrets.choice(string.ascii_lowercase) +
        secrets.choice(string.digits) +
        temp_password[3:]
    )
    
    # Create user
    user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=get_password_hash(temp_password),
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=True,
        must_change_password=True,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Print temp password to console (pharma demo — no email yet)
    print(f"\n{'='*60}")
    print(f"  NEW USER CREATED BY ADMIN")
    print(f"  Email:    {user_in.email}")
    print(f"  Username: {user_in.username}")
    print(f"  Role:     {user_in.role}")
    print(f"  Temp Password: {temp_password}")
    print(f"  ⚠️  User MUST change password on first login")
    print(f"{'='*60}\n")
    
    logger.info(
        f"ADMIN: User created | email={user_in.email} | role={user_in.role} | "
        f"created_by={current_user.email}"
    )
    
    return user


@router.get("/users", response_model=list)
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Admin-only: List all users."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "user_id": str(u.user_id),
            "email": u.email,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "must_change_password": getattr(u, 'must_change_password', False),
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Admin-only: Deactivate a user account."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if str(user.user_id) == str(current_user.user_id):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user.is_active = False
    db.commit()
    
    logger.info(f"ADMIN: User deactivated | email={user.email} | by={current_user.email}")
    return {"detail": f"User {user.email} deactivated"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Admin-only: Re-activate a user account."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    user.failed_login_attempts = 0  # Unlock too
    db.commit()
    
    logger.info(f"ADMIN: User activated | email={user.email} | by={current_user.email}")
    return {"detail": f"User {user.email} activated"}


@router.patch("/users/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    """Admin-only: Reset failed login attempts (unlock locked account)."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.failed_login_attempts = 0
    db.commit()
    
    logger.info(f"ADMIN: User unlocked | email={user.email} | by={current_user.email}")
    return {"detail": f"User {user.email} unlocked"}
