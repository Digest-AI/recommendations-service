from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


class EventSource:
    AFISHA_MD = "afisha_md"
    ITICKET_MD = "iticket_md"
    MTICKET_MD = "mticket_md"
    FEST_MD = "fest_md"
    CINEPLEX_MD = "cineplex_md"

    ALL = (AFISHA_MD, ITICKET_MD, MTICKET_MD, FEST_MD, CINEPLEX_MD)


class EventCategory:
    CONCERT = "concert"
    THEATRE = "theatre"
    MOVIE = "movie"
    SPORT = "sport"
    PARTY = "party"
    KIDS = "kids"
    TRAINING = "training"
    EXHIBITION = "exhibition"
    FESTIVAL = "festival"
    FREE = "free"
    OTHER = "other"

    ALL = (
        CONCERT, THEATRE, MOVIE, SPORT, PARTY, KIDS,
        TRAINING, EXHIBITION, FESTIVAL, FREE, OTHER,
    )


@dataclass(frozen=True)
class EventDTO:
    """Local representation of an Event fetched from the parser service.

    Mirrors the parser's `events` table. Lives in this service as a plain
    dataclass so the recommender doesn't depend on the parser's models.
    """

    id: str
    source: str
    url: str
    title: str
    title_ru: str = ""
    title_ro: str = ""
    description: str = ""
    description_ru: str = ""
    description_ro: str = ""
    category: str = EventCategory.OTHER
    raw_categories: tuple[str, ...] = ()
    date_start: datetime | None = None
    date_end: datetime | None = None
    venue_name: str = ""
    venue_address: str = ""
    city: str = ""
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    currency: str = "MDL"
    is_free: bool = False
    image_url: str = ""
    ticket_links: dict[str, str] = field(default_factory=dict)

    def localized_title(self, language: str) -> str:
        return {"ru": self.title_ru, "ro": self.title_ro}.get(language) or self.title

    def localized_description(self, language: str) -> str:
        return (
            {"ru": self.description_ru, "ro": self.description_ro}.get(language)
            or self.description
        )


@dataclass(frozen=True)
class EventFilters:
    """Hard filters applied before scoring."""

    cities: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    free_only: bool = False
    max_price: Decimal | None = None
    starts_after: datetime | None = None
    starts_before: datetime | None = None
    sources: tuple[str, ...] = ()
