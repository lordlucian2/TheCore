from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Iterable

from .engine import StudyGhost
from .engine import StudentProfile
from .engine import LocalSyncEngine
from .session import RoomType


class PresenceState(str, Enum):
    FOCUSING = "focusing"
    BREAK = "break"
    IDLE = "idle"
    OFFLINE = "offline"


@dataclass(slots=True)
class RoomTimer:
    cycle_type: str
    duration_seconds: int
    started_at: datetime
    last_sync_at: datetime | None = None
    paused: bool = False

    def elapsed_seconds(self, now: datetime | None = None) -> int:
        now = now or datetime.now(tz=self.started_at.tzinfo)
        if self.paused:
            return int((self.last_sync_at or now - timedelta(0)).total_seconds())
        return max(int((now - self.started_at).total_seconds()), 0)

    def remaining_seconds(self, now: datetime | None = None) -> int:
        return max(self.duration_seconds - self.elapsed_seconds(now), 0)

    def to_dict(self) -> dict[str, object]:
        return {
            "cycle_type": self.cycle_type,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat(),
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "paused": self.paused,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RoomTimer":
        return cls(
            cycle_type=data["cycle_type"],
            duration_seconds=int(data["duration_seconds"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_sync_at=datetime.fromisoformat(data["last_sync_at"]) if data.get("last_sync_at") else None,
            paused=bool(data.get("paused", False)),
        )

    def sync_offset_millis(self, server_time: datetime) -> int:
        return int((server_time - self.started_at).total_seconds() * 1000)

    def is_active(self, now: datetime | None = None) -> bool:
        return self.remaining_seconds(now) > 0 and not self.paused


@dataclass(slots=True)
class StudyRoom:
    room_id: str
    room_type: RoomType
    participant_ids: set[str] = field(default_factory=set)
    presence: dict[str, PresenceState] = field(default_factory=dict)
    last_seen_at: dict[str, datetime] = field(default_factory=dict)
    ambient_mode: str = "lofi"
    timer: RoomTimer | None = None

    def add_participant(self, student_id: str) -> None:
        self.participant_ids.add(student_id)
        self.presence.setdefault(student_id, PresenceState.OFFLINE)

    def remove_participant(self, student_id: str) -> None:
        self.participant_ids.discard(student_id)
        self.presence.pop(student_id, None)
        self.last_seen_at.pop(student_id, None)

    def update_presence(self, student_id: str, state: PresenceState, timestamp: datetime) -> None:
        self.add_participant(student_id)
        self.presence[student_id] = state
        self.last_seen_at[student_id] = timestamp

    def current_participants(self) -> list[str]:
        return [student_id for student_id in self.participant_ids if self.presence.get(student_id) != PresenceState.OFFLINE]

    def offline_ghosts(self, students: Iterable[StudentProfile], engine: LocalSyncEngine) -> list[StudyGhost]:
        ghosts: list[StudyGhost] = []
        for student in students:
            if student.student_id not in self.participant_ids or self.presence.get(student.student_id) == PresenceState.OFFLINE:
                ghost = engine.ghost_for(student)
                if ghost:
                    ghosts.append(ghost)
        return ghosts

    def to_dict(self) -> dict[str, object]:
        return {
            "room_id": self.room_id,
            "room_type": self.room_type.value,
            "participant_ids": list(self.participant_ids),
            "presence": {sid: state.value for sid, state in self.presence.items()},
            "last_seen_at": {sid: ts.isoformat() for sid, ts in self.last_seen_at.items()},
            "ambient_mode": self.ambient_mode,
            "timer": self.timer.to_dict() if self.timer else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "StudyRoom":
        timer_data = data.get("timer")
        timer = RoomTimer.from_dict(timer_data) if timer_data else None
        room = cls(
            room_id=data["room_id"],
            room_type=RoomType(data["room_type"]),
            participant_ids=set(data.get("participant_ids", [])),
            presence={sid: PresenceState(value) for sid, value in data.get("presence", {}).items()},
            last_seen_at={sid: datetime.fromisoformat(value) for sid, value in data.get("last_seen_at", {}).items()},
            ambient_mode=data.get("ambient_mode", "lofi"),
            timer=timer,
        )
        return room
