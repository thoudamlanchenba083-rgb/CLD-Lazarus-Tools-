"""Pydantic schemas for camera events and snapshot operations."""
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.camera_event import CameraEventType


class CameraEventCreate(BaseModel):
    """Camera event submission."""
    event_type: CameraEventType


class CameraEventResponse(BaseModel):
    """Camera event response."""
    id: int
    event_type: CameraEventType
    consent_id: int | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class SnapshotUploadResponse(BaseModel):
    """Response after voluntary test snapshot upload."""
    saved: bool
    filename: str
    size_bytes: int
    uploaded_at: datetime
