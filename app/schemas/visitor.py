"""Pydantic schemas for visitor operations."""
from datetime import datetime
from pydantic import BaseModel, Field


class VisitorCreate(BaseModel):
    """Request to create an anonymous visitor. No personal data needed."""
    pass


class VisitorResponse(BaseModel):
    """Response after creating a visitor."""
    visitor_uuid: str
    created_at: datetime

    model_config = {"from_attributes": True}
