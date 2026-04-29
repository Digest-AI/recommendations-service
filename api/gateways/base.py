from __future__ import annotations

from typing import Protocol

from api.dto import EventDTO, EventFilters


class EventGateway(Protocol):
    """Source of truth for event data.

    Implementations:
      - InMemoryEventGateway: seeded list, used in dev and tests.
      - HttpEventGateway: calls the parser service over HTTP. Add when the
        parser API contract is known.
    """

    def list(self, filters: EventFilters) -> list[EventDTO]: ...

    def get(self, event_id: str) -> EventDTO | None: ...
