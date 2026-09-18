"""Package data models and schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Package(BaseModel):
    """Package model representing a tracked package."""
    
    id: UUID
    tracking_no: str
    carrier: str
    recipient_id: UUID
    status: str
    notes: str | None = None
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
    notes: str | None = Field(None, max_length=500)


class PackageUpdate(BaseModel):
    """Schema for updating a package."""
    
    tracking_no: str | None = Field(None, min_length=1, max_length=100)
    carrier: str | None = Field(None, min_length=1, max_length=100)
    recipient_id: UUID | None = None
    notes: str | None = Field(None, max_length=500)


class PackageStatusUpdate(BaseModel):
    """Schema for updating package status."""
    
    status: str = Field(..., pattern="^(awaiting_pickup|out_for_delivery|delivered|returned)$")
    notes: str | None = Field(None, max_length=500)


class PackageEvent(BaseModel):
    """Package event model representing a status change."""
    
    id: UUID
    package_id: UUID
    old_status: str | None = None
    new_status: str
    notes: str | None = None
    actor_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class PackageEventCreate(BaseModel):
    """Schema for creating a package event."""
    
    package_id: UUID
    old_status: str | None = None
    new_status: str
    notes: str | None = Field(None, max_length=500)
    actor_id: UUID


class PackagePublic(BaseModel):
    """Public package information with recipient details."""
    
    id: UUID
    tracking_no: str
    carrier: str
    recipient_id: UUID
    recipient_name: str
    recipient_department: str | None = None
    status: str
    notes: str | None = None
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
    recipient_department: str | None = None
    status: str
    notes: str | None = None
    created_by: UUID
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    timeline: list[PackageEvent] = []


class PackageFilters(BaseModel):
    """Filters for package search."""
    
    query: str | None = None  # Search in tracking_no, recipient name
    status: str | None = None
    department: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    date_field: str = "created_at"
    recipient_id: UUID | None = None
    created_by: UUID | None = None


class Pagination(BaseModel):
    """Pagination parameters."""
    
    limit: int = Field(25, ge=1, le=100)
    offset: int = Field(0, ge=0)
