"""TheCore foundational domain package."""

from .analytics import StudentSnapshot, monthly_pulse_ranking, predicted_grade
from .engine import LocalSyncEngine, StudyEvent, StudyGhost, StudentProfile, SyncBatch
from .quests import Quest, QuestType, generate_tutorial_quests
from .service import TheCoreService
from .squad import SquadDashboard
from .storage import SQLiteEventStore

__all__ = [
    "LocalSyncEngine",
    "StudyEvent",
    "StudyGhost",
    "StudentProfile",
    "SyncBatch",
    "Quest",
    "QuestType",
    "generate_tutorial_quests",
    "SquadDashboard",
    "StudentSnapshot",
    "predicted_grade",
    "monthly_pulse_ranking",
    "SQLiteEventStore",
    "TheCoreService",
]
