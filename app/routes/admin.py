"""Admin routes & WebSocket hub for real-time dashboard updates."""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketClose
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, SessionLocal
from app.models.session import SessionRecord, SessionStatus
from app.websocket.manager import manager

logger = logging.getLogger("brAInfection.admin")
router = APIRouter(tags=["admin"])


def _verify_admin(x_admin_token: str | None = Header(default=None)):
    """V1-compatible admin token check."""
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token.")


@router.get("/api/sessions")
def list_sessions(
    x_admin_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """List recent sessions (admin only). V1-compatible endpoint."""
    _verify_admin(x_admin_token)
    rows = (
        db.query(SessionRecord)
        .order_by(SessionRecord.started_at.desc())
        .limit(250)
        .all()
    )
    result = []
    for s in rows:
        entry = {
            "id": s.session_uuid,
            "created_at": s.started_at.isoformat() if s.started_at else None,
            "status": s.status.value if s.status else None,
            "camera_permission": "not_requested",
            "location_permission": "not_requested",
            "latitude": None,
            "longitude": None,
            "accuracy": None,
            "platform": None,
            "user_agent": None,
        }
        if s.device_details:
            d = s.device_details[0]
            entry["platform"] = d.os or d.browser or ""
            entry["user_agent"] = d.user_agent or ""
        if s.location_updates:
            loc = s.location_updates[-1]
            entry["latitude"] = loc.latitude
            entry["longitude"] = loc.longitude
            entry["accuracy"] = loc.accuracy
            entry["location_permission"] = "granted"
        if s.camera_events:
            for evt in s.camera_events:
                if evt.event_type.value == "PERMISSION_GRANTED":
                    entry["camera_permission"] = "granted"
                    break
                elif evt.event_type.value == "PERMISSION_DENIED":
                    entry["camera_permission"] = "denied"
        result.append(entry)
    return result


@router.websocket("/ws/admin")
async def admin_websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    admin_session: str | None = Cookie(default=None),
):
    """Admin real-time WebSocket connection.

    Accepts only authenticated admins (via admin_session cookie or query token).
    Maintains heartbeat ping and drops dead connections.
    """
    settings = get_settings()
    # Check credentials during handshake
    auth_valid = False
    if token and token == settings.admin_token:
        auth_valid = True
    elif admin_session and admin_session == settings.admin_token:
        auth_valid = True

    if not auth_valid:
        # Reject handshake with 1008 Policy Violation
        await websocket.close(code=1008, reason="Authentication failed")
        logger.warning("Unauthenticated WebSocket handshake rejected")
        return

    await manager.connect(websocket)

    try:
        # Loop with heartbeat handling
        while True:
            # Wait for client heartbeat ping or message with timeout
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=45.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send server ping to keepalive
                await websocket.send_json({"type": "ping", "time": datetime.now(timezone.utc).isoformat()})
    except (WebSocketDisconnect, Exception) as e:
        manager.disconnect(websocket)
        logger.info("Admin WebSocket connection closed: %s", e)
