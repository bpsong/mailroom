"""Session data models."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class Session(BaseModel):
    """Session model representing an authenticated user session."""
    
    id: UUID
    user_id: UUID
    token: str
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    """Schema for creating a new session."""
    
    user_id: UUID
    token: str
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
