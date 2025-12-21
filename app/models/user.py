"""User data models and schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class User(BaseModel):
    """User model representing a system user."""
    
    id: UUID
    username: str
    password_hash: str
    full_name: str
    role: str  # 'super_admin', 'admin', 'operator'
    is_active: bool = True
    must_change_password: bool = False
    password_history: Optional[str] = None  # JSON array of previous hashes
    failed_login_count: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=12)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(super_admin|admin|operator)$")


class UserPublic(BaseModel):
    """Public user information (without sensitive data)."""
    
    id: UUID
    username: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
