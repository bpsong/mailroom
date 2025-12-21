"""Attachment data models and schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """Attachment model representing a package photo."""
    
    id: UUID
    package_id: UUID
    filename: str
    file_path: str
    mime_type: str
    file_size: int
    uploaded_by: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class AttachmentCreate(BaseModel):
    """Schema for creating an attachment."""
    
    package_id: UUID
    filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    mime_type: str = Field(..., min_length=1, max_length=100)
    file_size: int = Field(..., gt=0)
    uploaded_by: UUID


class AttachmentPublic(BaseModel):
    """Public attachment information."""
    
    id: UUID
    package_id: UUID
    filename: str
    file_path: str
    mime_type: str
    file_size: int
    uploaded_by: UUID
    uploaded_by_name: str
    created_at: datetime
