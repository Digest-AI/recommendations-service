from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from api.dto import EventCategory, EventDTO, EventFilters, EventSource


class InMemoryEventGateway:
    """Holds events in process memory. Used until the parser HTTP client lands.

    Loaded once at startup. Filtering is a linear scan — fine for the
    seed dataset (dozens of events).
    """

    def __init__(self, events: list[EventDTO]):
        self._events = events
        self._by_id = {event.id: event for event in events}

    @classmethod
    def from_seed_file(cls) -> InMemoryEventGateway:
        seed_path = Path(__file__).with_name("seed_events.json")
        if not seed_path.exists():
            return cls(_default_seed())
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
        return cls([_event_from_json(item) for item in raw])

    def list(self, filters: EventFilters) -> list[EventDTO]:
        result: list[EventDTO] = []
        for event in self._events:
            if not self._passes(event, filters):
                continue
            result.append(event)
        return result

    def get(self, event_id: str) -> EventDTO | None:
        return self._by_id.get(event_id)

    @staticmethod
    def _passes(event: EventDTO, filters: EventFilters) -> bool:
        if filters.cities and event.city not in filters.cities:
            return False
        if filters.categories and event.category not in filters.categories:
            return False
        if filters.sources and event.source not in filters.sources:
            return False
        if filters.free_only and not event.is_free:
            return False
        if filters.max_price is not None and not event.is_free:
            price = event.price_from
            if price is None or price > filters.max_price:
                return False
        if filters.starts_after is not None:
            if event.date_start is None or event.date_start < filters.starts_after:
                return False
        if filters.starts_before is not None:
            if event.date_start is None or event.date_start > filters.starts_before:
                return False
        return True


def _event_from_json(item: dict[str, Any]) -> EventDTO:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    def parse_dt(iso_value: Any, days_offset: Any) -> datetime | None:
        if iso_value:
            return datetime.fromisoformat(str(iso_value))
        if days_offset is not None:
            return now + timedelta(days=float(days_offset))
        return None

    def parse_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    return EventDTO(
        id=str(item["id"]),
        source=item["source"],
        url=item["url"],
        title=item.get("title", ""),
        title_ru=item.get("title_ru", ""),
        title_ro=item.get("title_ro", ""),
        description=item.get("description", ""),
        description_ru=item.get("description_ru", ""),
        description_ro=item.get("description_ro", ""),
        category=item.get("category", EventCategory.OTHER),
        raw_categories=tuple(item.get("raw_categories", []) or []),
        date_start=parse_dt(item.get("date_start"), item.get("date_start_in_days")),
        date_end=parse_dt(item.get("date_end"), item.get("date_end_in_days")),
        venue_name=item.get("venue_name", ""),
        venue_address=item.get("venue_address", ""),
        city=item.get("city", "Кишинёв"),
        price_from=parse_decimal(item.get("price_from")),
        price_to=parse_decimal(item.get("price_to")),
        currency=item.get("currency", "MDL"),
        is_free=bool(item.get("is_free", False)),
        image_url=item.get("image_url", ""),
        ticket_links=item.get("ticket_links", {}) or {},
    )


def _default_seed() -> list[EventDTO]:
    """Fallback seed if the JSON file is missing — keeps the service runnable."""
    now = datetime.now(timezone.utc).replace(microsecond=0)

    def days(n: int) -> datetime:
        return now + timedelta(days=n)

    return [
        EventDTO(
            id="seed-1",
            source=EventSource.AFISHA_MD,
            url="https://afisha.md/seed-1",
            title="Symphonic Rock Night",
            title_ru="Симфонический рок-вечер",
            title_ro="Seara de rock simfonic",
            category=EventCategory.CONCERT,
            raw_categories=("rock", "symphonic", "live music"),
            date_start=days(3),
            venue_name="Palatul Național",
            city="Кишинёв",
            price_from=Decimal("250"),
            price_to=Decimal("800"),
        ),
        EventDTO(
            id="seed-2",
            source=EventSource.CINEPLEX_MD,
            url="https://cineplex.md/seed-2",
            title="Dune: Part Three",
            category=EventCategory.MOVIE,
            raw_categories=("sci-fi", "imax"),
            date_start=days(1),
            venue_name="Cineplex Malldova",
            city="Кишинёв",
            price_from=Decimal("120"),
        ),
        EventDTO(
            id="seed-3",
            source=EventSource.FEST_MD,
            url="https://fest.md/seed-3",
            title="Open-air jazz in the park",
            category=EventCategory.CONCERT,
            raw_categories=("jazz", "open-air", "free"),
            date_start=days(5),
            venue_name="Parcul Valea Morilor",
            city="Кишинёв",
            is_free=True,
        ),
    ]
