"""Package data models and schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class Package(BaseModel):
    """Package model representing a tracked package."""
    
    id: UUID
    tracking_no: str
    carrier: str
    recipient_id: UUID
    status: str
    notes: Optional[str] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PackageCreate(BaseModel):
    """Schema for creating a new package."""
    
    tracking_no: str = Field(..., min_length=1, max_length=100)
    carrier: str = Field(..., min_length=1, max_length=100)
    recipient_id: UUID
    notes: Optional[str] = Field(None, max_length=500)


class PackageUpdate(BaseModel):
    """Schema for updating a package."""
    
    tracking_no: Optional[str] = Field(None, min_length=1, max_length=100)
    carrier: Optional[str] = Field(None, min_length=1, max_length=100)
    recipient_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=500)


class PackageStatusUpdate(BaseModel):
    """Schema for updating package status."""
    
    status: str = Field(..., pattern="^(awaiting_pickup|out_for_delivery|delivered|returned)$")
    notes: Optional[str] = Field(None, max_length=500)


class PackageEvent(BaseModel):
    """Package event model representing a status change."""
    
    id: UUID
    package_id: UUID
    old_status: Optional[str] = None
    new_status: str
    notes: Optional[str] = None
    actor_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class PackageEventCreate(BaseModel):
    """Schema for creating a package event."""
    
    package_id: UUID
    old_status: Optional[str] = None
    new_status: str
    notes: Optional[str] = Field(None, max_length=500)
    actor_id: UUID


class PackagePublic(BaseModel):
    """Public package information with recipient details."""
    
    id: UUID
    tracking_no: str
    carrier: str
    recipient_id: UUID
    recipient_name: str
    recipient_department: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_by: UUID
    created_by_name: str
    created_at: datetime
    updated_at: datetime


class PackageDetail(BaseModel):
    """Detailed package information with timeline."""
    
    id: UUID
    tracking_no: str
    carrier: str
    recipient_id: UUID
    recipient_name: str
    recipient_email: str
    recipient_department: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_by: UUID
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    timeline: List[PackageEvent] = []


class PackageFilters(BaseModel):
    """Filters for package search."""
    
    query: Optional[str] = None  # Search in tracking_no, recipient name
    status: Optional[str] = None
    department: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    recipient_id: Optional[UUID] = None
    created_by: Optional[UUID] = None


class Pagination(BaseModel):
    """Pagination parameters."""
    
    limit: int = Field(25, ge=1, le=100)
    offset: int = Field(0, ge=0)
