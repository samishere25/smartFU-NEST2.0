"""
Security utilities - using Argon2 (better than bcrypt)
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

# Password hasher - Argon2 (no 72 byte limit!)
ph = PasswordHasher()

# JWT Bearer token
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2"""
    return ph.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token and return payload dict with user_id and role"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            return None
        
        return {"user_id": user_id, "role": payload.get("role")}
        
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    from app.models.user import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    token_data = decode_token(token)
    
    # Support both old (string) and new (dict) return format
    if token_data is None:
        raise credentials_exception
    
    if isinstance(token_data, dict):
        user_identifier = token_data.get("user_id")
    else:
        user_identifier = token_data
    
    if user_identifier is None:
        raise credentials_exception
    
    # Try to find user by email first (since JWT tokens use email in 'sub')
    user = db.query(User).filter(User.email == user_identifier).first()
    
    # If not found by email, try by user_id
    if user is None:
        try:
            user = db.query(User).filter(User.user_id == user_identifier).first()
        except:
            pass
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user"""
    return current_user


def require_role(required_roles):
    """Dependency to require one of the specified roles.
    
    Usage:
        @router.get("/...", dependencies=[Depends(require_role(["ADMIN"]))])
        @router.get("/...", dependencies=[Depends(require_role(["REVIEWER", "ADMIN"]))])
    
    Accepts a single string or list of strings.
    """
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    async def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(required_roles)}. Your role: {current_user.role}"
            )
        return current_user
    
    return role_checker


def require_permission(permission: str):
    """Dependency to require specific permission"""
    async def permission_checker(current_user = Depends(get_current_user)):
        if permission not in (current_user.permissions or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission {permission} required"
            )
        return current_user
    
    return permission_checker
