"""Authentication event data models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuthEvent(BaseModel):
    """Authentication event model for audit logging."""
    
    id: UUID
    user_id: UUID | None = None
    event_type: str  # 'login', 'login_failed', 'logout', 'password_change', etc.
    username: str | None = None
    ip_address: str | None = None
    details: str | None = None  # JSON string for additional data
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthEventCreate(BaseModel):
    """Schema for creating an authentication event."""
    
    user_id: UUID | None = None
    event_type: str
    username: str | None = None
    ip_address: str | None = None
    details: str | None = None
