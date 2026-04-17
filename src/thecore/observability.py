from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(slots=True)
class SyncMetrics:
    """Tracks offline sync reliability metrics."""

    events_recorded: int = 0
    events_acknowledged: int = 0
    sync_batches_created: int = 0
    sync_batches_acknowledged: int = 0
    duplicate_nonce_rejections: int = 0
    last_sync_at: Optional[datetime] = None


@dataclass(slots=True)
class RoomMetrics:
    """Tracks room presence and subscription metrics."""

    total_rooms_created: int = 0
    active_room_subscriptions: int = 0
    presence_updates_broadcast: int = 0
    websocket_connections_opened: int = 0
    websocket_connections_closed: int = 0
    last_broadcast_at: Optional[datetime] = None


@dataclass(slots=True)
class VaultMetrics:
    """Tracks Vault resource sharing metrics."""

    resources_created: int = 0
    resource_votes_cast: int = 0
    most_voted_resource: Optional[str] = None
    last_resource_created_at: Optional[datetime] = None


@dataclass(slots=True)
class AIMetrics:
    """Tracks AI scaffolding usage."""

    queries_logged: int = 0
    responses_logged: int = 0
    hint_mode_used: int = 0
    step_by_step_mode_used: int = 0
    solution_mode_used: int = 0
    last_query_at: Optional[datetime] = None


@dataclass(slots=True)
class ObservabilityCollector:
    """Centralized metrics collection for TheCore system."""

    sync: SyncMetrics = field(default_factory=SyncMetrics)
    room: RoomMetrics = field(default_factory=RoomMetrics)
    vault: VaultMetrics = field(default_factory=VaultMetrics)
    ai: AIMetrics = field(default_factory=AIMetrics)

    def record_event_recorded(self) -> None:
        """Record a study event being logged."""
        self.sync.events_recorded += 1

    def record_event_acknowledged(self) -> None:
        """Record a study event being acknowledged in sync."""
        self.sync.events_acknowledged += 1

    def record_sync_batch_created(self) -> None:
        """Record a sync batch being created."""
        self.sync.sync_batches_created += 1
        self.sync.last_sync_at = datetime.now(tz=timezone.utc)

    def record_sync_batch_acknowledged(self) -> None:
        """Record a sync batch being acknowledged."""
        self.sync.sync_batches_acknowledged += 1

    def record_duplicate_nonce(self) -> None:
        """Record a duplicate nonce rejection."""
        self.sync.duplicate_nonce_rejections += 1

    def record_room_created(self) -> None:
        """Record a room being created."""
        self.room.total_rooms_created += 1

    def record_websocket_connected(self) -> None:
        """Record a WebSocket connection opened."""
        self.room.websocket_connections_opened += 1
        self.room.active_room_subscriptions += 1

    def record_websocket_disconnected(self) -> None:
        """Record a WebSocket connection closed."""
        self.room.websocket_connections_closed += 1
        if self.room.active_room_subscriptions > 0:
            self.room.active_room_subscriptions -= 1

    def record_presence_broadcast(self) -> None:
        """Record a presence update being broadcast."""
        self.room.presence_updates_broadcast += 1
        self.room.last_broadcast_at = datetime.now(tz=timezone.utc)

    def record_resource_created(self) -> None:
        """Record a Vault resource being created."""
        self.vault.resources_created += 1
        self.vault.last_resource_created_at = datetime.now(tz=timezone.utc)

    def record_resource_vote(self, resource_id: str) -> None:
        """Record a vote on a Vault resource."""
        self.vault.resource_votes_cast += 1
        self.vault.most_voted_resource = resource_id

    def record_ai_query(self, mode: str) -> None:
        """Record an AI query being logged."""
        self.ai.queries_logged += 1
        if mode == "hint":
            self.ai.hint_mode_used += 1
        elif mode == "step_by_step":
            self.ai.step_by_step_mode_used += 1
        elif mode == "solution":
            self.ai.solution_mode_used += 1
        self.ai.last_query_at = datetime.now(tz=timezone.utc)

    def record_ai_response(self) -> None:
        """Record an AI response being logged."""
        self.ai.responses_logged += 1

    def to_dict(self) -> dict:
        """Export metrics as a dictionary for JSON serialization."""
        return {
            "sync": {
                "events_recorded": self.sync.events_recorded,
                "events_acknowledged": self.sync.events_acknowledged,
                "sync_batches_created": self.sync.sync_batches_created,
                "sync_batches_acknowledged": self.sync.sync_batches_acknowledged,
                "duplicate_nonce_rejections": self.sync.duplicate_nonce_rejections,
                "last_sync_at": self.sync.last_sync_at.isoformat() if self.sync.last_sync_at else None,
            },
            "room": {
                "total_rooms_created": self.room.total_rooms_created,
                "active_room_subscriptions": self.room.active_room_subscriptions,
                "presence_updates_broadcast": self.room.presence_updates_broadcast,
                "websocket_connections_opened": self.room.websocket_connections_opened,
                "websocket_connections_closed": self.room.websocket_connections_closed,
                "last_broadcast_at": self.room.last_broadcast_at.isoformat() if self.room.last_broadcast_at else None,
            },
            "vault": {
                "resources_created": self.vault.resources_created,
                "resource_votes_cast": self.vault.resource_votes_cast,
                "most_voted_resource": self.vault.most_voted_resource,
                "last_resource_created_at": self.vault.last_resource_created_at.isoformat()
                if self.vault.last_resource_created_at
                else None,
            },
            "ai": {
                "queries_logged": self.ai.queries_logged,
                "responses_logged": self.ai.responses_logged,
                "hint_mode_used": self.ai.hint_mode_used,
                "step_by_step_mode_used": self.ai.step_by_step_mode_used,
                "solution_mode_used": self.ai.solution_mode_used,
                "last_query_at": self.ai.last_query_at.isoformat() if self.ai.last_query_at else None,
            },
        }


# Global metrics instance
metrics = ObservabilityCollector()
