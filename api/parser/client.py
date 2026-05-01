from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from api.parser.mapping import rankable_from_parser_payload
from api.recommendations.types import RankableEvent

logger = logging.getLogger(__name__)

SCRAPED_ON_PATH = "api/events/scraped-on/"
DETAIL_PATH_FMT = "api/events/{id}/"


class ParserClient:
    """HTTP client for the parser service (scraped-on list + optional detail)."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        page_size: int = 100,
        retries: int = 2,
        retry_backoff: float = 0.5,
        accept_language: str = "ru",
    ) -> None:
        root = base_url.rstrip("/") + "/"
        if not root.startswith(("http://", "https://")):
            raise RuntimeError("EVENTS_API_BASE_URL must be an absolute http(s) URL")
        self._base_url = root
        self._timeout = timeout
        self._page_size = page_size
        self._retries = retries
        self._retry_backoff = retry_backoff
        self._accept_language = accept_language

    def fetch_scraped_on(self, date_iso: str) -> list[RankableEvent]:
        """GET /api/events/scraped-on/?date=YYYY-MM-DD (all pages)."""
        results: list[RankableEvent] = []
        params: dict[str, Any] = {"date": date_iso, "page_size": self._page_size}
        path = SCRAPED_ON_PATH
        next_url: str | None = None
        page = 1

        while True:
            if next_url:
                payload = self._get_json_url(next_url)
            else:
                q = {**params, "page": page}
                payload = self._get_json_path(path, q)

            if payload is None:
                break

            for item in payload.get("results") or []:
                if isinstance(item, dict):
                    r = rankable_from_parser_payload(item)
                    if r is not None:
                        results.append(r)

            next_url = payload.get("next")
            if not next_url:
                break
            page += 1

        return results

    def fetch_rankable_detail(self, event_id: int) -> RankableEvent | None:
        path = DETAIL_PATH_FMT.format(id=event_id)
        payload = self._get_json_path(path, {})
        if payload is None or not isinstance(payload, dict):
            return None
        return rankable_from_parser_payload(payload)

    def _get_json_path(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        url = urljoin(self._base_url, path.lstrip("/"))
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        return self._get_json_url(url)

    def _get_json_url(self, url: str) -> dict[str, Any] | None:
        request = Request(url, headers={"Accept": "application/json", "Accept-Language": self._accept_language})

        attempt = 0
        body: bytes | None = None
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
            except (URLError, TimeoutError, OSError) as exc:
                if attempt >= self._retries:
                    logger.warning("Parser unreachable (%s) on %s", exc, url)
                    return None
            attempt += 1
            time.sleep(self._retry_backoff * attempt)

        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning("Parser invalid JSON on %s: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None
