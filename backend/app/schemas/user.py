"""
User Schemas
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re

# Valid roles for access control
VALID_ROLES = {"PV_SPECIALIST", "SAFETY_OFFICER", "ADMIN", "PROCESSOR", "REVIEWER", "GOVERNANCE"}

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    role: str = "PV_SPECIALIST"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        v = v.upper() if isinstance(v, str) else v
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError("Username may only contain letters, numbers, dots, hyphens, and underscores")
        return v
    
class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one digit")
        return v
    
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    
class UserInDB(UserBase):
    user_id: UUID
    is_active: bool
    must_change_password: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        
class User(UserInDB):
    pass

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInDB
    password_change_required: bool = False
    
class TokenData(BaseModel):
    user_id: Optional[str] = None


# ── Admin-only user creation (no public signup) ──────────────
class AdminCreateUser(BaseModel):
    """Admin creates a user — system generates temp password."""
    email: EmailStr
    username: str
    role: str = "PROCESSOR"
    full_name: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        v = v.upper() if isinstance(v, str) else v
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError("Username may only contain letters, numbers, dots, hyphens, and underscores")
        return v


class ChangePassword(BaseModel):
    """Password change request."""
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one digit")
        return v
