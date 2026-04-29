from django.conf import settings

from .base import EventGateway
from .http import HttpEventGateway
from .in_memory import InMemoryEventGateway

_gateway: EventGateway | None = None


def get_event_gateway() -> EventGateway:
    """Return the active event source.

    Selected via the EVENT_GATEWAY setting. Defaults to "in_memory".
    Set EVENT_GATEWAY=http (and EVENTS_API_BASE_URL) to talk to the
    parser service.
    """
    global _gateway
    if _gateway is not None:
        return _gateway

    backend = getattr(settings, "EVENT_GATEWAY", "in_memory")
    if backend == "in_memory":
        _gateway = InMemoryEventGateway.from_seed_file()
    elif backend == "http":
        _gateway = HttpEventGateway(base_url=settings.EVENTS_API_BASE_URL)
    else:
        raise RuntimeError(f"Unknown EVENT_GATEWAY backend: {backend}")
    return _gateway


__all__ = ["EventGateway", "get_event_gateway"]
