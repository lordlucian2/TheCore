from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


@dataclass(slots=True)
class VaultResource:
    resource_id: str
    author_id: str
    title: str
    subject: str
    description: str
    tags: list[str]
    content_url: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    upvotes: int = 0
    downvotes: int = 0
    featured: bool = False
    visibility: str = "public"

    def score(self) -> int:
        return self.upvotes - self.downvotes

    def vote(self, upvote: bool = True) -> None:
        if upvote:
            self.upvotes += 1
        else:
            self.downvotes += 1

    def add_tags(self, new_tags: Iterable[str]) -> None:
        self.tags = list(dict.fromkeys(self.tags + list(new_tags)))

    def mark_updated(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
