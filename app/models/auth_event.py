"""Authentication event data models."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AuthEvent(BaseModel):
    """Authentication event model for audit logging."""
    
    id: UUID
    user_id: Optional[UUID] = None
    event_type: str  # 'login', 'login_failed', 'logout', 'password_change', etc.
    username: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[str] = None  # JSON string for additional data
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthEventCreate(BaseModel):
    """Schema for creating an authentication event."""
    
    user_id: Optional[UUID] = None
    event_type: str
    username: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[str] = None
