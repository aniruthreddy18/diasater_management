"""
WebSocket Connection Manager for Real-Time Map & Dashboard Streaming
Multi-Disaster Early Warning System
"""

import json
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages active WebSocket connections from browser dashboards,
    broadcasting telemetry events, state updates, and alerts in real-time.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket client connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Client connected to WebSocket stream. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Client disconnected from WebSocket. Remaining: %d", len(self.active_connections))

    async def broadcast(self, message_type: str, data: dict) -> None:
        """Broadcast payload to all active clients."""
        if not self.active_connections:
            return

        payload = {
            "type": message_type,
            "data": data,
        }
        msg_str = json.dumps(payload)

        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(msg_str)
            except Exception as e:
                logger.debug("Failed sending to client: %s", e)
                dead_connections.append(connection)

        for dead in dead_connections:
            if dead in self.active_connections:
                self.active_connections.remove(dead)


# Global WebSocket manager instance
ws_manager = WebSocketManager()
