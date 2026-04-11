"""Carrier data models and schemas."""

from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field


class Carrier(BaseModel):
    """Carrier model representing a shipping carrier."""

    id: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CarrierCreate(BaseModel):
    """Schema for creating a new carrier."""

    name: Annotated[str, Field(min_length=1, max_length=100)]


class CarrierUpdate(BaseModel):
    """Schema for updating a carrier."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
