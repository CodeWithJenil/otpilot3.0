"""Search strategy contracts for limiting email downloads."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    since: datetime | None = None
    unseen_only: bool = True
    sender: str | None = None
    subject_contains: str | None = None
    recipient: str | None = None
    body_contains: str | None = None
    limit: int = 10


@dataclass(frozen=True, slots=True)
class SearchQuery:
    terms: tuple[str, ...] = field(default_factory=tuple)


class SearchStrategy(Protocol):
    name: str

    def build(self, criteria: SearchCriteria) -> SearchQuery:
        """Build a provider-level query from normalized search criteria."""

