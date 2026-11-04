"""Visitor routes — create anonymous visitors."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.visitor import VisitorCreate, VisitorResponse
from app.services.session_service import create_visitor

logger = logging.getLogger("brAInfection.visitors")
router = APIRouter(prefix="/api/visitors", tags=["visitors"])


@router.post("", response_model=VisitorResponse, status_code=201)
def create_visitor_endpoint(db: Session = Depends(get_db)):
    """Create an anonymous visitor with a random UUID.

    No personal data is required or stored at this step.
    """
    visitor = create_visitor(db)
    logger.info("Visitor created: %s", visitor.visitor_uuid)
    return visitor
