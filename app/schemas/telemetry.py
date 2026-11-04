"""Pydantic schemas for telemetry and device/location data."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from app.models.telemetry_event import TelemetryEventType


class DeviceSubmit(BaseModel):
    """Device metadata submitted by the visitor."""
    user_agent: str = Field(default="", max_length=600)
    language: str = Field(default="", max_length=80)
    timezone: str = Field(default="", max_length=80)
    screen_width: int | None = Field(default=None, ge=0, le=20000)
    screen_height: int | None = Field(default=None, ge=0, le=20000)
    online: bool | None = Field(default=None)


class DeviceResponse(BaseModel):
    """Device metadata stored on server."""
    id: int
    browser: str | None = None
    os: str | None = None
    device_type: str | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    language: str | None = None
    timezone: str | None = None
    online: bool | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class LocationSubmit(BaseModel):
    """Location data submitted by the visitor."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100000)


class LocationResponse(BaseModel):
    """Location update recorded response."""
    id: int
    latitude: float
    longitude: float
    accuracy: float | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class TelemetryItem(BaseModel):
    """Single telemetry item within a batched request."""
    event_type: TelemetryEventType
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class TelemetryBatchSubmit(BaseModel):
    """Batched events submitted by visitor."""
    events: list[TelemetryItem] = Field(..., min_length=1, max_length=50)


class TelemetryBatchResponse(BaseModel):
    """Batch recording response."""
    received: int
    recorded: int
