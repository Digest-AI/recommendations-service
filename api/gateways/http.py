from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from django.core.cache import cache

from api.dto import EventCategory, EventDTO, EventFilters

logger = logging.getLogger(__name__)


class HttpEventGateway:
    """Talks to the parser service over HTTP.

    Contract: see `apidocparser.md`. The live OpenAPI schema returns
    snake_case JSON (despite the doc claiming camelCase) — we read it
    verbatim, no key transformation.
    """

    LIST_PATH = "/api/events/upcoming/"
    DETAIL_PATH_FMT = "/api/events/{id}/"

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        page_size: int = 100,
        max_pages: int = 5,
        list_cache_ttl: int = 60,
        detail_cache_ttl: int = 300,
        accept_language: str = "ru",
        retries: int = 2,
        retry_backoff: float = 0.5,
    ):
        if not base_url:
            raise RuntimeError(
                "HttpEventGateway requires EVENTS_API_BASE_URL to be set."
            )
        self._base_url = base_url.rstrip("/") + "/"
        self._timeout = timeout
        self._page_size = page_size
        self._max_pages = max_pages
        self._list_ttl = list_cache_ttl
        self._detail_ttl = detail_cache_ttl
        self._accept_language = accept_language
        self._retries = retries
        self._retry_backoff = retry_backoff

    # ---- public API ----

    def list(self, filters: EventFilters) -> list[EventDTO]:
        params = self._params_from_filters(filters)
        cache_key = self._list_cache_key(params)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        events: list[EventDTO] = []
        for page in range(1, self._max_pages + 1):
            page_params = {**params, "page": page, "page_size": self._page_size}
            payload = self._get_json(self.LIST_PATH, page_params)
            if payload is None:
                break
            for item in payload.get("results") or []:
                events.append(_event_from_payload(item))
            if not payload.get("next"):
                break

        # Apply client-side filters that the parser doesn't expose natively.
        if filters.free_only:
            events = [e for e in events if e.is_free]

        cache.set(cache_key, events, self._list_ttl)
        return events

    def get(self, event_id: str) -> EventDTO | None:
        cache_key = f"events:detail:{event_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        payload = self._get_json(self.DETAIL_PATH_FMT.format(id=event_id), {})
        if payload is None:
            return None
        event = _event_from_payload(payload)
        cache.set(cache_key, event, self._detail_ttl)
        return event

    # ---- internals ----

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        url = urljoin(self._base_url, path.lstrip("/"))
        if params:
            url = f"{url}?{urlencode(params, doseq=False)}"
        request = Request(url, headers={"Accept-Language": self._accept_language})

        attempt = 0
        while True:
            try:
                with urlopen(request, timeout=self._timeout) as response:
                    body = response.read()
                break
            except HTTPError as exc:
                if exc.code == 404:
                    return None
                if exc.code < 500 or attempt >= self._retries:
                    logger.warning("Parser HTTP error %s on %s", exc.code, url)
                    return None
            except (URLError, TimeoutError) as exc:
                if attempt >= self._retries:
                    logger.warning("Parser unreachable (%s) on %s", exc, url)
                    return None
            attempt += 1
            time.sleep(self._retry_backoff * attempt)

        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning("Parser returned invalid JSON on %s: %s", url, exc)
            return None

    @staticmethod
    def _params_from_filters(filters: EventFilters) -> dict[str, Any]:
        """Translate `EventFilters` → parser query params (snake_case)."""
        params: dict[str, Any] = {}
        if filters.cities:
            params["city"] = filters.cities[0]
        if filters.categories:
            params["category"] = ",".join(filters.categories)
        if filters.sources:
            params["provider"] = filters.sources[0]
        if filters.max_price is not None:
            params["price_max"] = str(filters.max_price)
        if filters.starts_after is not None:
            params["date_from"] = filters.starts_after.date().isoformat()
        if filters.starts_before is not None:
            params["date_to"] = filters.starts_before.date().isoformat()
        params["ordering"] = "date_start"
        return params

    @staticmethod
    def _list_cache_key(params: dict[str, Any]) -> str:
        items = sorted(params.items())
        return "events:list:" + "&".join(f"{k}={v}" for k, v in items)


def _event_from_payload(item: dict[str, Any]) -> EventDTO:
    """Build an EventDTO from a parser payload (snake_case JSON)."""

    provider = item.get("provider") or {}
    categories = item.get("categories") or []
    category_slugs = [c.get("slug", "") for c in categories if c.get("slug")]
    primary_category = category_slugs[0] if category_slugs else EventCategory.OTHER
    raw_categories = tuple(category_slugs[1:]) if len(category_slugs) > 1 else ()

    price_from = _parse_decimal(item.get("price_from"))
    price_to = _parse_decimal(item.get("price_to"))
    is_free = price_from is None or price_from == 0

    tickets_url = item.get("tickets_url") or ""
    ticket_links = {provider.get("slug") or "primary": tickets_url} if tickets_url else {}

    return EventDTO(
        id=str(item.get("id", "")),
        source=str(provider.get("slug") or ""),
        url=item.get("url") or "",
        title=item.get("title_ru") or item.get("title_ro") or "",
        title_ru=item.get("title_ru") or "",
        title_ro=item.get("title_ro") or "",
        description=item.get("description_ru") or item.get("description_ro") or "",
        description_ru=item.get("description_ru") or "",
        description_ro=item.get("description_ro") or "",
        category=primary_category,
        raw_categories=raw_categories,
        date_start=_parse_dt(item.get("date_start")),
        date_end=_parse_dt(item.get("date_end")),
        venue_name=item.get("place") or "",
        venue_address=item.get("address") or "",
        city=item.get("city") or "",
        price_from=price_from,
        price_to=price_to,
        currency="MDL",
        is_free=is_free,
        image_url=item.get("image_url") or "",
        ticket_links=ticket_links,
    )


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
