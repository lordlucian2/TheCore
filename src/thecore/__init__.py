"""TheCore foundational domain package."""

from .analytics import StudentSnapshot, monthly_pulse_ranking, predicted_grade
from .engine import LocalSyncEngine, StudyEvent, StudyGhost, StudentProfile, SyncBatch
from .quests import Quest, QuestType, generate_tutorial_quests
from .room import PresenceState, RoomTimer, StudyRoom
from .squad import SquadDashboard
from .service import TheCoreService
from .session import RoomType, StudySession, xp_for_session
from .storage import SQLiteAIStore, SQLiteEventStore, SQLiteRoomStore, SQLiteVaultStore
from .vault import VaultResource
from .ai import AIQuery, AIResponse, AIResponseMode, ClutchAI

__all__ = [
    "LocalSyncEngine",
    "StudyEvent",
    "StudyGhost",
    "StudentProfile",
    "SyncBatch",
    "Quest",
    "QuestType",
    "generate_tutorial_quests",
    "PresenceState",
    "RoomTimer",
    "StudyRoom",
    "SquadDashboard",
    "StudentSnapshot",
    "predicted_grade",
    "monthly_pulse_ranking",
    "VaultResource",
    "AIQuery",
    "AIResponse",
    "AIResponseMode",
    "ClutchAI",
    "SQLiteAIStore",
    "SQLiteEventStore",
    "SQLiteRoomStore",
    "SQLiteVaultStore",
    "TheCoreService",
]
