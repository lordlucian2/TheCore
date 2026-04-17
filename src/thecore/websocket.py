from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import asyncio
import json

from fastapi import WebSocket


@dataclass(slots=True)
class RoomPresenceUpdate:
    """Broadcast event for room presence changes."""

    room_id: str
    student_id: str
    state: str  # e.g., 'focusing', 'break', 'offline'
    timestamp: str


class RoomSubscriptionManager:
    """Manages WebSocket subscriptions for room presence updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.room_locks: dict[str, asyncio.Lock] = {}

    async def connect(self, room_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection for a room."""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
            self.room_locks[room_id] = asyncio.Lock()
        self.active_connections[room_id].append(websocket)
        
        from .observability import metrics
        metrics.record_websocket_connected()

    async def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection from a room."""
        async with self.room_locks[room_id]:
            if room_id in self.active_connections:
                self.active_connections[room_id].remove(websocket)
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
                    del self.room_locks[room_id]
        
        from .observability import metrics
        metrics.record_websocket_disconnected()

    async def broadcast(self, room_id: str, message: dict[str, str]) -> None:
        """Broadcast a presence update to all clients subscribed to a room."""
        if room_id not in self.active_connections:
            return

        from .observability import metrics
        metrics.record_presence_broadcast()
        
        async with self.room_locks[room_id]:
            disconnected = []
            for connection in self.active_connections.get(room_id, []):
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            # Remove disconnected clients
            for conn in disconnected:
                try:
                    await self.disconnect(room_id, conn)
                except Exception:
                    pass

    def get_room_subscriber_count(self, room_id: str) -> int:
        """Get the number of active subscribers for a room."""
        return len(self.active_connections.get(room_id, []))

    def get_active_rooms(self) -> list[str]:
        """List all rooms with active subscriptions."""
        return list(self.active_connections.keys())


# Global instance for managing all room subscriptions
manager = RoomSubscriptionManager()
