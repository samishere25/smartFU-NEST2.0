"""
Authentication routes. Admin creates users via /api/admin/create-user.
Login returns JWT with role claim. Password change enforced on first login.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
import logging

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _HAS_SLOWAPI = True
except ImportError:
    _HAS_SLOWAPI = False

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserInDB, ChangePassword
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    get_current_user
)

router = APIRouter()

# Security logger
security_logger = logging.getLogger("smartfu.security")

# Rate limiter
if _HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = None

# Account lockout settings
MAX_FAILED_ATTEMPTS = 5

def _noop_decorator(fn):
    return fn


@router.post("/login", response_model=Token)
@(limiter.limit("10/minute") if limiter else _noop_decorator)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return JWT. Sets password_change_required if needed."""
    
    client_ip = request.client.host if request.client else "unknown"
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        security_logger.warning(
            f"SECURITY: Failed login — unknown email | email={form_data.username} | ip={client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.failed_login_attempts and user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        security_logger.warning(
            f"SECURITY: Locked account login attempt | email={user.email} | attempts={user.failed_login_attempts} | ip={client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked after {MAX_FAILED_ATTEMPTS} failed attempts. Contact an administrator."
        )
    
    if not verify_password(form_data.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        db.commit()
        
        security_logger.warning(
            f"SECURITY: Failed login — wrong password | email={user.email} | "
            f"attempt={user.failed_login_attempts}/{MAX_FAILED_ATTEMPTS} | ip={client_ip}"
        )
        
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked after {MAX_FAILED_ATTEMPTS} failed attempts. Contact an administrator."
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        security_logger.warning(
            f"SECURITY: Inactive account login attempt | email={user.email} | ip={client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    db.commit()
    
    must_change = getattr(user, 'must_change_password', False) or False
    
    security_logger.info(
        f"SECURITY: Successful login | email={user.email} | role={user.role} | "
        f"must_change_password={must_change} | ip={client_ip}"
    )
    
    token_data = {"sub": str(user.user_id), "role": user.role}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,  # 30 minutes
        user=UserInDB.model_validate(user),
        password_change_required=must_change,
    )


@router.post("/change-password")
async def change_password(
    payload: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change password. Requires valid JWT and correct current password."""
    
    if not verify_password(payload.old_password, current_user.password_hash):
        security_logger.warning(
            f"SECURITY: Password change failed — wrong old password | email={current_user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password"
        )
    
    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.commit()
    
    security_logger.info(
        f"SECURITY: Password changed successfully | email={current_user.email}"
    )
    
    return {"detail": "Password changed successfully"}


@router.get("/me", response_model=UserInDB)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user
