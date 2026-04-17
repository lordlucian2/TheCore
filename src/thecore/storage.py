from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import sqlite3

from .ai import AIQuery, AIResponse, AIResponseMode
from .engine import StudentProfile, StudyEvent
from .session import RoomType
from .vault import VaultResource


@dataclass(slots=True)
class SQLiteEventStore:
    """Minimal durable event log for offline-first sync."""

    db_path: str = ":memory:"
    _conn: sqlite3.Connection = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
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


@dataclass(slots=True)
class SQLiteVaultStore:
    db_path: str = ":memory:"
    _conn: sqlite3.Connection = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vault_resources (
                resource_id TEXT PRIMARY KEY,
                author_id TEXT NOT NULL,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                tags TEXT NOT NULL,
                content_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                upvotes INTEGER NOT NULL,
                downvotes INTEGER NOT NULL,
                featured INTEGER NOT NULL,
                visibility TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def add(self, resource: VaultResource) -> None:
        self._conn.execute(
            """
            INSERT INTO vault_resources(
                resource_id, author_id, title, subject, description, tags,
                content_url, created_at, updated_at, upvotes, downvotes,
                featured, visibility
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resource.resource_id,
                resource.author_id,
                resource.title,
                resource.subject,
                resource.description,
                json.dumps(resource.tags),
                resource.content_url,
                resource.created_at.isoformat(),
                resource.updated_at.isoformat(),
                resource.upvotes,
                resource.downvotes,
                int(resource.featured),
                resource.visibility,
            ),
        )
        self._conn.commit()

    def load(
        self,
        resource_id: str | None = None,
        author_id: str | None = None,
        subject: str | None = None,
    ) -> list[VaultResource]:
        query = "SELECT * FROM vault_resources"
        conditions = []
        params: list[str] = []

        if resource_id is not None:
            conditions.append("resource_id = ?")
            params.append(resource_id)
        if author_id is not None:
            conditions.append("author_id = ?")
            params.append(author_id)
        if subject is not None:
            conditions.append("subject = ?")
            params.append(subject)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        rows = self._conn.execute(query, tuple(params)).fetchall()
        return [
            VaultResource(
                resource_id=row["resource_id"],
                author_id=row["author_id"],
                title=row["title"],
                subject=row["subject"],
                description=row["description"],
                tags=json.loads(row["tags"]),
                content_url=row["content_url"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                upvotes=row["upvotes"],
                downvotes=row["downvotes"],
                featured=bool(row["featured"]),
                visibility=row["visibility"],
            )
            for row in rows
        ]

    def vote(self, resource_id: str, upvote: bool = True) -> int:
        if upvote:
            self._conn.execute(
                "UPDATE vault_resources SET upvotes = upvotes + 1 WHERE resource_id = ?",
                (resource_id,),
            )
        else:
            self._conn.execute(
                "UPDATE vault_resources SET downvotes = downvotes + 1 WHERE resource_id = ?",
                (resource_id,),
            )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT upvotes, downvotes FROM vault_resources WHERE resource_id = ?",
            (resource_id,),
        ).fetchone()
        if row is None:
            raise ValueError("resource not found")
        return row["upvotes"] - row["downvotes"]

    def close(self) -> None:
        self._conn.close()


@dataclass(slots=True)
class SQLiteStudentStore:
    db_path: str = ":memory:"
    _conn: sqlite3.Connection = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                student_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                school TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def add(self, profile: StudentProfile) -> None:
        self._conn.execute(
            """
            INSERT INTO student_profiles(
                student_id, display_name, school, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                profile.student_id,
                profile.display_name,
                profile.school,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
        )
        self._conn.commit()

    def update(self, profile: StudentProfile) -> None:
        self._conn.execute(
            """
            UPDATE student_profiles
            SET display_name = ?, school = ?, updated_at = ?
            WHERE student_id = ?
            """,
            (
                profile.display_name,
                profile.school,
                datetime.now().isoformat(),
                profile.student_id,
            ),
        )
        self._conn.commit()

    def load(self, student_id: str | None = None) -> list[StudentProfile]:
        if student_id is None:
            rows = self._conn.execute(
                "SELECT student_id, display_name, school FROM student_profiles"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT student_id, display_name, school FROM student_profiles WHERE student_id = ?",
                (student_id,),
            ).fetchall()

        return [
            StudentProfile(
                student_id=row["student_id"],
                display_name=row["display_name"],
                school=row["school"],
            )
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()


@dataclass(slots=True)
class SQLiteRoomStore:
    db_path: str = ":memory:"
    _conn: sqlite3.Connection = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS study_rooms (
                room_id TEXT PRIMARY KEY,
                room_type TEXT NOT NULL,
                participant_ids TEXT NOT NULL,
                presence TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                ambient_mode TEXT NOT NULL,
                timer TEXT
            )
            """
        )
        self._conn.commit()

    def add(self, room: "StudyRoom") -> None:
        self._conn.execute(
            """
            INSERT INTO study_rooms(
                room_id, room_type, participant_ids, presence,
                last_seen_at, ambient_mode, timer
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                room.room_id,
                room.room_type.value,
                json.dumps(list(room.participant_ids)),
                json.dumps({sid: state.value for sid, state in room.presence.items()}),
                json.dumps({sid: dt.isoformat() for sid, dt in room.last_seen_at.items()}),
                room.ambient_mode,
                json.dumps(room.timer.to_dict()) if room.timer else None,
            ),
        )
        self._conn.commit()

    def update(self, room: "StudyRoom") -> None:
        self._conn.execute(
            """
            REPLACE INTO study_rooms(
                room_id, room_type, participant_ids, presence,
                last_seen_at, ambient_mode, timer
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                room.room_id,
                room.room_type.value,
                json.dumps(list(room.participant_ids)),
                json.dumps({sid: state.value for sid, state in room.presence.items()}),
                json.dumps({sid: dt.isoformat() for sid, dt in room.last_seen_at.items()}),
                room.ambient_mode,
                json.dumps(room.timer.to_dict()) if room.timer else None,
            ),
        )
        self._conn.commit()

    def load(self, room_id: str) -> "StudyRoom | None":
        row = self._conn.execute(
            "SELECT * FROM study_rooms WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        if row is None:
            return None

        from .room import PresenceState, RoomTimer, StudyRoom

        timer_data = json.loads(row["timer"]) if row["timer"] else None
        room = StudyRoom(
            room_id=row["room_id"],
            room_type=RoomType(row["room_type"]),
            participant_ids=set(json.loads(row["participant_ids"])),
            presence={sid: PresenceState(value) for sid, value in json.loads(row["presence"]).items()},
            last_seen_at={sid: datetime.fromisoformat(value) for sid, value in json.loads(row["last_seen_at"]).items()},
            ambient_mode=row["ambient_mode"],
            timer=RoomTimer.from_dict(timer_data) if timer_data else None,
        )
        return room

    def close(self) -> None:
        self._conn.close()


@dataclass(slots=True)
class SQLiteAIStore:
    db_path: str = ":memory:"
    _conn: sqlite3.Connection = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_queries (
                query_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                prompt TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                context TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_responses (
                query_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                text TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(query_id, created_at)
            )
            """
        )
        self._conn.commit()

    def append_query(self, query: AIQuery) -> None:
        self._conn.execute(
            """
            INSERT INTO ai_queries(query_id, student_id, subject, prompt, mode, created_at, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query.query_id,
                query.student_id,
                query.subject,
                query.prompt,
                query.mode.value,
                query.created_at.isoformat(),
                json.dumps(query.context),
            ),
        )
        self._conn.commit()

    def append_response(self, response: AIResponse) -> None:
        self._conn.execute(
            """
            INSERT INTO ai_responses(query_id, mode, text, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                response.query_id,
                response.mode.value,
                response.text,
                json.dumps(response.metadata),
                response.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def load_queries(self, student_id: str | None = None) -> list[AIQuery]:
        query = "SELECT * FROM ai_queries"
        params: tuple[str, ...] = ()
        if student_id is not None:
            query += " WHERE student_id = ?"
            params = (student_id,)

        rows = self._conn.execute(query, params).fetchall()
        return [
            AIQuery(
                query_id=row["query_id"],
                student_id=row["student_id"],
                subject=row["subject"],
                prompt=row["prompt"],
                mode=AIResponseMode(row["mode"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                context=json.loads(row["context"]),
            )
            for row in rows
        ]

    def load_responses(self, query_id: str) -> list[AIResponse]:
        rows = self._conn.execute(
            "SELECT * FROM ai_responses WHERE query_id = ? ORDER BY created_at ASC",
            (query_id,),
        ).fetchall()
        return [
            AIResponse(
                query_id=row["query_id"],
                mode=AIResponseMode(row["mode"]),
                text=row["text"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()
