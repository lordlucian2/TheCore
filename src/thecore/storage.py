from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import sqlite3

from .engine import StudyEvent


@dataclass(slots=True)
class SQLiteEventStore:
    """Minimal durable event log for offline-first sync."""

    db_path: str = ":memory:"
    _conn: sqlite3.Connection = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS study_events (
                student_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                value INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                nonce TEXT NOT NULL,
                PRIMARY KEY(student_id, nonce)
            )
            """
        )
        self._conn.commit()

    def append(self, event: StudyEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO study_events(student_id, kind, value, started_at, ended_at, nonce)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.student_id,
                event.kind,
                event.value,
                event.started_at.isoformat(),
                event.ended_at.isoformat(),
                event.nonce,
            ),
        )
        self._conn.commit()

    def load(self, student_id: str | None = None) -> list[StudyEvent]:
        if student_id is None:
            rows = self._conn.execute(
                "SELECT student_id, kind, value, started_at, ended_at, nonce FROM study_events"
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT student_id, kind, value, started_at, ended_at, nonce
                FROM study_events
                WHERE student_id = ?
                """,
                (student_id,),
            ).fetchall()

        return [
            StudyEvent(
                student_id=row["student_id"],
                kind=row["kind"],
                value=row["value"],
                started_at=datetime.fromisoformat(row["started_at"]),
                ended_at=datetime.fromisoformat(row["ended_at"]),
                nonce=row["nonce"],
            )
            for row in rows
        ]

    def delete_by_nonces(self, nonces: set[tuple[str, str]]) -> int:
        deleted = 0
        for student_id, nonce in nonces:
            cursor = self._conn.execute(
                "DELETE FROM study_events WHERE student_id = ? AND nonce = ?",
                (student_id, nonce),
            )
            deleted += cursor.rowcount
        self._conn.commit()
        return deleted

    def close(self) -> None:
        self._conn.close()
