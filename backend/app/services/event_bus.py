import json
import asyncio
from typing import Set, Any
from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections for the real-time order dashboard."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast an event payload to all connected clients."""
        text_data = json.dumps(message, default=str)
        async with self._lock:
            dead_connections = set()
            for connection in self.active_connections:
                try:
                    await connection.send_text(text_data)
                except Exception:
                    dead_connections.add(connection)

            for dead in dead_connections:
                self.active_connections.remove(dead)


manager = ConnectionManager()
