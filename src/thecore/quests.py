from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QuestType(str, Enum):
    DIFFERENCE_ENGINE = "difference_engine"
    WHY_BOUNTY = "why_bounty"
    SOCRATIC_DUEL = "socratic_duel"


@dataclass(slots=True)
class Quest:
    id: str
    title: str
    prompt: str
    quest_type: QuestType
    xp_reward: int
    min_rank: int


def generate_tutorial_quests() -> list[Quest]:
    """Scaffold first-week onboarding quests for new students."""

    return [
        Quest(
            id="q1",
            title="Difference Engine: Believability Check",
            prompt="Which statement is more believable and why in one sentence?",
            quest_type=QuestType.DIFFERENCE_ENGINE,
            xp_reward=100,
            min_rank=1,
        ),
        Quest(
            id="q2",
            title="Why Bounty: Break the Cycle",
            prompt="Name one thing that could disrupt a natural or social cycle.",
            quest_type=QuestType.WHY_BOUNTY,
            xp_reward=150,
            min_rank=2,
        ),
        Quest(
            id="q3",
            title="Socratic Duel: Catch the Flaw",
            prompt="Read AI's claim, identify the flaw, and submit a correction.",
            quest_type=QuestType.SOCRATIC_DUEL,
            xp_reward=200,
            min_rank=3,
        ),
    ]
