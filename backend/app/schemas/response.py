"""
API Response Schemas
"""

from pydantic import BaseModel
from typing import Optional, Any, Dict

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
