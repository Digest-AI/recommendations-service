from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class RankableEvent:
    """Minimal event shape used by ContentScorer / MMR (parser list or detail JSON)."""

    id: int
    category: str
    raw_categories: tuple[str, ...]
    source: str
    venue_name: str
    city: str
    date_start: datetime | None
    price_from: Decimal | None
    is_free: bool
