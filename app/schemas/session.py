"""Pydantic schemas for session operations."""
from datetime import datetime
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request to start a new session."""
    visitor_uuid: str = Field(..., max_length=36, description="UUID of the visitor")


class SessionResponse(BaseModel):
    """Response after creating a session."""
    session_uuid: str
    session_token: str
    status: str
    started_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class SessionInfo(BaseModel):
    """Public session info (for the session owner)."""
    session_uuid: str
    status: str
    started_at: datetime
    expires_at: datetime
    last_activity: datetime

    model_config = {"from_attributes": True}


class SessionEndResponse(BaseModel):
    """Response after ending a session."""
    session_uuid: str
    status: str
    ended_at: datetime

    model_config = {"from_attributes": True}


class HeartbeatRequest(BaseModel):
    """Heartbeat to keep the session alive."""
    pass


class HeartbeatResponse(BaseModel):
    """Heartbeat response."""
    session_uuid: str
    status: str
    last_activity: datetime
