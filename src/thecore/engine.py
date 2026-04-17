from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Iterable

from .session import StudySession, xp_for_session


@dataclass(slots=True)
class StudentProfile:
    student_id: str
    display_name: str
    school: str


@dataclass(slots=True)
class StudyEvent:
    student_id: str
    kind: str
    value: int
    started_at: datetime
    ended_at: datetime
    nonce: str

    @property
    def duration_seconds(self) -> int:
        return max(int((self.ended_at - self.started_at).total_seconds()), 0)


@dataclass(slots=True)
class StudyGhost:
    student_id: str
    display_name: str
    last_seen_at: datetime
    summary: str


@dataclass(slots=True)
class SyncBatch:
    student_id: str | None
    events: list[StudyEvent]
    signatures: list[str]


@dataclass(slots=True)
class LocalSyncEngine:
    """Offline-first event recorder with lightweight anti-spoof verification."""

    max_event_duration: timedelta = timedelta(hours=3)
    _events: list[StudyEvent] = field(default_factory=list)

    def record(self, event: StudyEvent) -> str:
        self._validate(event)
        if any(existing.student_id == event.student_id and existing.nonce == event.nonce for existing in self._events):
            raise ValueError("duplicate event nonce")
        self._events.append(event)
        return self._signature_for(event)

    def pending_events(self, student_id: str | None = None) -> list[StudyEvent]:
        if student_id is None:
            return list(self._events)
        return [event for event in self._events if event.student_id == student_id]

    def create_sync_batch(self, student_id: str | None = None) -> SyncBatch:
        events = self.pending_events(student_id)
        signatures = [self._signature_for(event) for event in events]
        return SyncBatch(student_id=student_id, events=events, signatures=signatures)

    def acknowledge_batch(self, batch: SyncBatch) -> dict[str, int]:
        if not self.verify_signatures(batch.events, batch.signatures):
            raise ValueError("invalid sync batch signatures")

        xp_total = sum(event.value for event in batch.events if event.kind == "xp")
        pomodoros = sum(event.value for event in batch.events if event.kind == "pomodoro")

        batch_keys = {(event.student_id, event.nonce) for event in batch.events}
        self._events = [
            event for event in self._events if (event.student_id, event.nonce) not in batch_keys
        ]

        return {"xp_total": xp_total, "pomodoros": pomodoros, "count": len(batch.events)}

    def burst_sync(self, student_id: str | None = None) -> dict[str, int]:
        selected = self.pending_events(student_id)
        xp_total = sum(event.value for event in selected if event.kind == "xp")
        pomodoros = sum(event.value for event in selected if event.kind == "pomodoro")

        if student_id is None:
            self._events.clear()
        else:
            self._events = [event for event in self._events if event.student_id != student_id]

        return {"xp_total": xp_total, "pomodoros": pomodoros, "count": len(selected)}
        xp_total = sum(event.value for event in selected if event.kind == "xp")
        pomodoros = sum(event.value for event in selected if event.kind == "pomodoro")

        if student_id is None:
            self._events.clear()
        else:
            self._events = [event for event in self._events if event.student_id != student_id]

        return {"xp_total": xp_total, "pomodoros": pomodoros, "count": len(selected)}

    def ghost_for(self, profile: StudentProfile) -> StudyGhost | None:
        events = self.pending_events(profile.student_id)
        if not events:
            return None

        last_event = max(events, key=lambda event: event.ended_at)
        summary = f"{profile.display_name} was active {last_event.kind} ({last_event.value})"
        return StudyGhost(
            student_id=profile.student_id,
            display_name=profile.display_name,
            last_seen_at=last_event.ended_at,
            summary=summary,
        )

    def verify_signatures(self, events: Iterable[StudyEvent], signatures: Iterable[str]) -> bool:
        computed = [self._signature_for(event) for event in events]
        return computed == list(signatures)

    def streak_for(self, student_id: str, as_of: datetime | None = None) -> int:
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        completed_dates = sorted(
            {event.ended_at.date() for event in self.pending_events(student_id)}
        )
        if not completed_dates:
            return 0

        streak = 0
        current_day = as_of.date()
        if current_day not in completed_dates:
            current_day -= timedelta(days=1)

        while current_day in completed_dates:
            streak += 1
            current_day -= timedelta(days=1)

        return streak

    def session_xp(self, session: StudySession) -> int:
        return xp_for_session(session)

    def _validate(self, event: StudyEvent) -> None:
        if event.value <= 0:
            raise ValueError("event value must be positive")

        if event.ended_at < event.started_at:
            raise ValueError("event cannot end before it starts")

        if event.ended_at - event.started_at > self.max_event_duration:
            raise ValueError("event duration exceeds allowed offline window")

        now = datetime.now(tz=timezone.utc)
        if event.ended_at > now + timedelta(minutes=5):
            raise ValueError("event cannot be from the far future")

    def _signature_for(self, event: StudyEvent) -> str:
        payload = (
            f"{event.student_id}|{event.kind}|{event.value}|"
            f"{event.started_at.isoformat()}|{event.ended_at.isoformat()}|{event.nonce}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
