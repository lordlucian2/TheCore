"""TheCore foundational domain package."""

from .engine import LocalSyncEngine, StudyEvent, StudyGhost, StudentProfile
from .quests import Quest, QuestType, generate_tutorial_quests
from .squad import SquadDashboard

__all__ = [
    "LocalSyncEngine",
    "StudyEvent",
    "StudyGhost",
    "StudentProfile",
    "Quest",
    "QuestType",
    "generate_tutorial_quests",
    "SquadDashboard",
]
