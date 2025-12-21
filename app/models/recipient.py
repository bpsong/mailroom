"""Recipient data models and schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class Recipient(BaseModel):
    """Recipient model representing an employee who receives packages."""
    
    id: UUID
    employee_id: str
    name: str
    email: str
    department: str
    phone: Optional[str] = None
    location: Optional[str] = None
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
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=100)


class RecipientUpdate(BaseModel):
    """Schema for updating a recipient."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=100)


class RecipientPublic(BaseModel):
    """Public recipient information."""
    
    id: UUID
    employee_id: str
    name: str
    email: str
    department: str
    phone: Optional[str] = None
    location: Optional[str] = None
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
