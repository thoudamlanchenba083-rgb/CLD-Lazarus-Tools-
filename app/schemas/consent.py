"""Pydantic schemas for consent operations."""
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.consent import ConsentType


class ConsentCreate(BaseModel):
    """Request to record a consent decision."""
    consent_type: ConsentType = Field(..., description="Type of consent being granted")
    granted: bool = Field(default=True, description="Whether consent is granted")


class ConsentResponse(BaseModel):
    """Response after recording consent."""
    id: int
    consent_type: ConsentType
    consent_version: int
    granted: bool
    recorded_at: datetime
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConsentRevokeResponse(BaseModel):
    """Response after revoking consent."""
    id: int
    consent_type: ConsentType
    revoked_at: datetime

    model_config = {"from_attributes": True}


class ConsentListResponse(BaseModel):
    """List of consent records for a session."""
    consents: list[ConsentResponse]
