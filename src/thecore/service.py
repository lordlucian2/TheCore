from __future__ import annotations

from dataclasses import dataclass

from .engine import LocalSyncEngine, StudyEvent, SyncBatch
from .storage import SQLiteEventStore


@dataclass(slots=True)
class TheCoreService:
    """Coordinates in-memory sync engine with durable local storage."""

    engine: LocalSyncEngine
    store: SQLiteEventStore

    @classmethod
    def from_store(cls, store: SQLiteEventStore) -> "TheCoreService":
        engine = LocalSyncEngine()
        for event in store.load():
            engine.record(event)
        return cls(engine=engine, store=store)

    def record_event(self, event: StudyEvent) -> str:
        signature = self.engine.record(event)
        self.store.append(event)
        return signature

    def create_batch(self, student_id: str | None = None) -> SyncBatch:
        return self.engine.create_sync_batch(student_id)

    def acknowledge_batch(self, batch: SyncBatch) -> dict[str, int]:
        aggregate = self.engine.acknowledge_batch(batch)
        keys = {(event.student_id, event.nonce) for event in batch.events}
        self.store.delete_by_nonces(keys)
        return aggregate
