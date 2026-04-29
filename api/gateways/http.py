from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from django.core.cache import cache

from api.dto import EventCategory, EventDTO, EventFilters
from utils.transformers import pythonize

logger = logging.getLogger(__name__)


class HttpEventGateway:
    """Talks to the parser service over HTTP.

    Contract is described in `apidocparser.md` at the repo root. Responses
    are camelCase JSON; we convert them to the snake_case `EventDTO`.

    Notes:
      - The list endpoint returns the lightweight serializer (no
        descriptions, no rawCategories). Detail data is filled in lazily
        via `get(event_id)` when the engine asks for it (e.g. when
        building UserContext from past interactions).
      - `list()` paginates up to `max_pages` * `page_size` candidates.
        That's the upper bound on what the recommender will ever see in
        one request — well above any realistic top_k.
      - Both `list()` and `get()` use Django's cache to avoid hammering
        the parser when many recommendation requests fire in a row.
    """

    LIST_PATH = "/api/events/"
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

    # ---- public API ----

    def list(self, filters: EventFilters) -> list[EventDTO]:
        params = self._params_from_filters(filters)
        cache_key = self._list_cache_key(params)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        events: list[EventDTO] = []
        for page in range(1, self._max_pages + 1):
            page_params = {**params, "page": page, "pageSize": self._page_size}
            payload = self._get_json(self.LIST_PATH, page_params)
            if payload is None:
                break
            results = payload.get("results") or []
            for item in results:
                events.append(_event_from_payload(pythonize(item)))
            if not payload.get("next"):
                break

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
        event = _event_from_payload(pythonize(payload))
        cache.set(cache_key, event, self._detail_ttl)
        return event

    # ---- internals ----

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        url = urljoin(self._base_url, path.lstrip("/"))
        if params:
            url = f"{url}?{urlencode(params, doseq=False)}"
        request = Request(url, headers={"Accept-Language": self._accept_language})
        try:
            with urlopen(request, timeout=self._timeout) as response:
                body = response.read()
        except HTTPError as exc:
            if exc.code == 404:
                return None
            logger.warning("Parser HTTP error %s on %s", exc.code, url)
            return None
        except (URLError, TimeoutError) as exc:
            logger.warning("Parser unreachable (%s) on %s", exc, url)
            return None

        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning("Parser returned invalid JSON on %s: %s", url, exc)
            return None

    @staticmethod
    def _params_from_filters(filters: EventFilters) -> dict[str, Any]:
        """Translate `EventFilters` → parser query params.

        The parser API accepts a single value per filter field. If our
        filters carry multiple values (e.g. several categories) we send
        the first — current callers only ever pass one, and the rest of
        the filtering is handled client-side after fetch.
        """
        params: dict[str, Any] = {}
        if filters.cities:
            params["city"] = filters.cities[0]
        if filters.categories:
            params["category"] = filters.categories[0]
        if filters.sources:
            params["source"] = filters.sources[0]
        if filters.free_only:
            params["isFree"] = "true"
        if filters.max_price is not None:
            params["priceMax"] = str(filters.max_price)
        if filters.starts_after is not None:
            params["dateFrom"] = filters.starts_after.date().isoformat()
        if filters.starts_before is not None:
            params["dateTo"] = filters.starts_before.date().isoformat()
        params["ordering"] = "dateStart"
        return params

    @staticmethod
    def _list_cache_key(params: dict[str, Any]) -> str:
        items = sorted(params.items())
        return "events:list:" + "&".join(f"{k}={v}" for k, v in items)


def _event_from_payload(item: dict[str, Any]) -> EventDTO:
    """Build an EventDTO from a snake_cased parser payload."""

    return EventDTO(
        id=str(item["id"]),
        source=item.get("source", ""),
        url=item.get("url", ""),
        title=item.get("title") or "",
        title_ru=item.get("title_ru") or "",
        title_ro=item.get("title_ro") or "",
        description=item.get("description") or "",
        description_ru=item.get("description_ru") or "",
        description_ro=item.get("description_ro") or "",
        category=item.get("category") or EventCategory.OTHER,
        raw_categories=tuple(item.get("raw_categories") or []),
        date_start=_parse_dt(item.get("date_start")),
        date_end=_parse_dt(item.get("date_end")),
        venue_name=item.get("venue_name") or "",
        venue_address=item.get("venue_address") or "",
        city=item.get("city") or "",
        price_from=_parse_decimal(item.get("price_from")),
        price_to=_parse_decimal(item.get("price_to")),
        currency=item.get("currency") or "MDL",
        is_free=bool(item.get("is_free", False)),
        image_url=item.get("image_url") or "",
        ticket_links=item.get("ticket_links") or {},
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
