"""Recipient data models and schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Recipient(BaseModel):
    """Recipient model representing an employee who receives packages."""
    
    id: UUID
    employee_id: str
    name: str
    email: str
    department: str
    phone: str | None = None
    location: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RecipientCreate(BaseModel):
    """Schema for creating a new recipient."""
    
    employee_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=100, pattern=r".*\S.*")  # Must contain non-whitespace
    phone: str | None = Field(None, max_length=20)
    location: str | None = Field(None, max_length=100)


class RecipientUpdate(BaseModel):
    """Schema for updating a recipient."""
    
    name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    department: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    location: str | None = Field(None, max_length=100)


class RecipientPublic(BaseModel):
    """Public recipient information."""
    
    id: UUID
    employee_id: str
    name: str
    email: str
    department: str
    phone: str | None = None
    location: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RecipientSearchResult(BaseModel):
    """Recipient search result for autocomplete."""
    
    id: UUID
    employee_id: str
    name: str
    email: str
    department: str
