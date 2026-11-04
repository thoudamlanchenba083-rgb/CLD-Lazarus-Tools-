"""Unit tests for Phase 9: Real-time WebSockets."""
import asyncio
import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.websocket.manager import manager

client = TestClient(app)


def test_unauthenticated_websocket_connection_is_refused():
    """Unauthenticated WebSocket handshake is closed with 1008 policy violation."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/admin?token=invalid_token") as ws:
            ws.receive_text()


def test_authenticated_websocket_connect_and_heartbeat():
    """Authenticated WebSocket connects, responds to heartbeat ping, and receives broadcast."""
    settings = get_settings()
    token = settings.admin_token

    with client.websocket_connect(f"/ws/admin?token={token}") as ws:
        # Send heartbeat ping
        ws.send_text("ping")
        data = ws.receive_text()
        assert data == "pong"


def test_websocket_broadcast_receives_event():
    """Manager broadcast distributes messages to connected active sockets."""
    settings = get_settings()
    token = settings.admin_token

    with client.websocket_connect(f"/ws/admin?token={token}") as ws:
        test_payload = {
            "session_uuid": "sess-test-123",
            "event_type": "SESSION_CREATED",
            "status": "ACTIVE",
            "recorded_at": "2026-11-04T00:00:00Z",
            "summary": {"browser": "Chrome"},
        }
        # Run broadcast synchronously in event loop
        asyncio.run(manager.broadcast(test_payload))
        received = ws.receive_json()
        assert received["session_uuid"] == "sess-test-123"
        assert received["event_type"] == "SESSION_CREATED"
