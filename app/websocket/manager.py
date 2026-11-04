"""WebSocket connection manager for real-time admin updates."""
import asyncio
import logging
from typing import List
from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger("brAInfection.websocket")


class ConnectionManager:
    """Manages WebSocket connections, heartbeats, and event broadcasting to admins."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept connection and add to active pool."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Admin WebSocket connected. Total active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove connection from active pool."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Admin WebSocket disconnected. Total active: %d", len(self.active_connections))

    async def broadcast(self, message: dict):
        """Broadcast minimal summary event to all connected admin clients."""
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
                else:
                    dead_connections.append(connection)
            except Exception as e:
                logger.warning("Error broadcasting to connection: %s", e)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


manager = ConnectionManager()
