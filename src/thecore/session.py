from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class RoomType(str, Enum):
    SOLO = "solo"
    GROUP = "group"
    SUBJECT = "subject"


@dataclass(slots=True)
class StudySession:
    session_id: str
    student_id: str
    room_type: RoomType
    started_at: datetime
    ended_at: datetime
    completed_pomodoros: int = 0
    is_first_session_of_day: bool = False
    bonus_xp: int = 0

    @property
    def duration_minutes(self) -> int:
        seconds = max(int((self.ended_at - self.started_at).total_seconds()), 0)
        return max(1, seconds // 60)


def xp_for_session(session: StudySession) -> int:
    multipliers = {
        RoomType.SOLO: 1.0,
        RoomType.GROUP: 1.25,
        RoomType.SUBJECT: 1.1,
    }

    base_minutes = session.duration_minutes
    multiplier = multipliers.get(session.room_type, 1.0)
    xp = int(base_minutes * multiplier)

    bonus = 0
    if session.completed_pomodoros >= 1:
        bonus += 50
    if session.completed_pomodoros >= 4:
        bonus += 50
    if session.is_first_session_of_day:
        bonus += 25

    return xp + bonus + session.bonus_xp
