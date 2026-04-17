from __future__ import annotations

from dataclasses import dataclass

from .ai import AIQuery, AIResponse
from .engine import LocalSyncEngine, StudentProfile, StudyEvent, SyncBatch
from .room import StudyRoom
from .session import RoomType
from .storage import SQLiteAIStore, SQLiteEventStore, SQLiteRoomStore, SQLiteStudentStore, SQLiteVaultStore
from .vault import VaultResource
from .observability import metrics


@dataclass(slots=True)
class TheCoreService:
    """Coordinates in-memory sync engine with durable local storage."""

    engine: LocalSyncEngine
    store: SQLiteEventStore
    vault_store: SQLiteVaultStore | None = None
    ai_store: SQLiteAIStore | None = None
    room_store: SQLiteRoomStore | None = None
    student_store: SQLiteStudentStore | None = None

    @classmethod
    def from_store(
        cls,
        store: SQLiteEventStore,
        vault_store: SQLiteVaultStore | None = None,
        ai_store: SQLiteAIStore | None = None,
        room_store: SQLiteRoomStore | None = None,
        student_store: SQLiteStudentStore | None = None,
    ) -> "TheCoreService":
        engine = LocalSyncEngine()
        for event in store.load():
            engine.record(event)
        return cls(
            engine=engine,
            store=store,
            vault_store=vault_store,
            ai_store=ai_store,
            room_store=room_store,
            student_store=student_store,
        )

    def record_event(self, event: StudyEvent) -> str:
        signature = self.engine.record(event)
        self.store.append(event)
        metrics.record_event_recorded()
        return signature

    def create_batch(self, student_id: str | None = None) -> SyncBatch:
        batch = self.engine.create_sync_batch(student_id)
        metrics.record_sync_batch_created()
        return batch

    def acknowledge_batch(self, batch: SyncBatch) -> dict[str, int]:
        aggregate = self.engine.acknowledge_batch(batch)
        keys = {(event.student_id, event.nonce) for event in batch.events}
        self.store.delete_by_nonces(keys)
        metrics.record_sync_batch_acknowledged()
        for _ in batch.events:
            metrics.record_event_acknowledged()
        return aggregate

    def record_student(self, profile: StudentProfile) -> None:
        if self.student_store is None:
            raise ValueError("student store is not configured")
        self.student_store.add(profile)

    def update_student(self, profile: StudentProfile) -> None:
        if self.student_store is None:
            raise ValueError("student store is not configured")
        self.student_store.update(profile)

    def load_student(self, student_id: str | None = None) -> list[StudentProfile]:
        if self.student_store is None:
            raise ValueError("student store is not configured")
        return self.student_store.load(student_id)

    def record_resource(self, resource: VaultResource) -> None:
        if self.vault_store is None:
            raise ValueError("vault store is not configured")
        self.vault_store.add(resource)
        metrics.record_resource_created()

    def vote_resource(self, resource_id: str, upvote: bool = True) -> int:
        if self.vault_store is None:
            raise ValueError("vault store is not configured")
        score = self.vault_store.vote(resource_id, upvote=upvote)
        metrics.record_resource_vote(resource_id)
        return score

    def load_resources(
        self,
        resource_id: str | None = None,
        author_id: str | None = None,
        subject: str | None = None,
    ) -> list[VaultResource]:
        if self.vault_store is None:
            raise ValueError("vault store is not configured")
        return self.vault_store.load(resource_id=resource_id, author_id=author_id, subject=subject)

    def create_room(self, room: StudyRoom) -> None:
        if self.room_store is None:
            raise ValueError("room store is not configured")
        self.room_store.add(room)
        metrics.record_room_created()

    def update_room(self, room: StudyRoom) -> None:
        if self.room_store is None:
            raise ValueError("room store is not configured")
        self.room_store.update(room)

    def load_room(self, room_id: str) -> StudyRoom | None:
        if self.room_store is None:
            raise ValueError("room store is not configured")
        return self.room_store.load(room_id)

    def log_ai_query(self, query: AIQuery) -> None:
        if self.ai_store is None:
            raise ValueError("AI store is not configured")
        self.ai_store.append_query(query)
        metrics.record_ai_query(query.mode.value)

    def log_ai_response(self, response: AIResponse) -> None:
        if self.ai_store is None:
            raise ValueError("AI store is not configured")
        self.ai_store.append_response(response)
        metrics.record_ai_response()

    def load_ai_queries(self, student_id: str | None = None) -> list[AIQuery]:
        if self.ai_store is None:
            raise ValueError("AI store is not configured")
        return self.ai_store.load_queries(student_id)

    def load_ai_responses(self, query_id: str) -> list[AIResponse]:
        if self.ai_store is None:
            raise ValueError("AI store is not configured")
        return self.ai_store.load_responses(query_id)
