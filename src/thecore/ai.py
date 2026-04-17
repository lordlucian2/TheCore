from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AIResponseMode(str, Enum):
    HINT = "hint"
    STEP_BY_STEP = "step_by_step"
    SOLUTION = "solution"


@dataclass(slots=True)
class AIQuery:
    query_id: str
    student_id: str
    subject: str
    prompt: str
    mode: AIResponseMode
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AIResponse:
    query_id: str
    mode: AIResponseMode
    text: str
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ClutchAI:
    """Socratic AI scaffold for hint/step-by-step/solution responses."""

    def generate_response(self, query: AIQuery) -> AIResponse:
        if query.mode == AIResponseMode.HINT:
            text = self._hint_text(query)
        elif query.mode == AIResponseMode.STEP_BY_STEP:
            text = self._step_by_step_text(query)
        else:
            text = self._solution_text(query)

        metadata = {
            "subject": query.subject,
            "mode": query.mode.value,
        }
        return AIResponse(query_id=query.query_id, mode=query.mode, text=text, metadata=metadata)

    def _hint_text(self, query: AIQuery) -> str:
        return f"Try breaking the problem into smaller parts and ask: what is the key idea behind {query.subject}?"

    def _step_by_step_text(self, query: AIQuery) -> str:
        return f"Let's walk through this one step at a time for {query.subject}. Start by identifying the facts, then the goal, then the next action."

    def _solution_text(self, query: AIQuery) -> str:
        return f"Here is a guided answer for {query.subject}: focus on the main concept, then apply it directly to the prompt."
