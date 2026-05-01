"""Daily 10:00 push to the Telegram bot service.

For every user that has a `tg_id` and at least one `is_new=True`
recommendation, POST a payload to the bot. The `is_new` flag is NOT
flipped — the user-facing `GET /api/recommendations/` endpoint owns
that state transition.

Bot contract: `POST /api/recommendations/`. The bot's published
OpenAPI does not document a request body, so we send a structured
payload that includes the Telegram id and a compact rec list. Adjust
the payload shape here if the bot exposes a stricter schema later.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from django.conf import settings

from api.models import Recommendation, UserProfile

logger = logging.getLogger(__name__)


@dataclass
class NotifyStats:
    eligible_users: int
    notified: int
    failed: int
    total_recs: int


def notify_telegram_bot() -> NotifyStats:
    base_url = getattr(settings, "TG_SERVICE_BASE_URL", "")
    if not base_url:
        logger.error("notify_telegram_bot: TG_SERVICE_BASE_URL not configured")
        return NotifyStats(0, 0, 0, 0)

    profiles = list(
        UserProfile.objects.filter(tg_id__isnull=False).values("user_id", "tg_id", "language")
    )
    notified = 0
    failed = 0
    total_recs = 0

    for profile in profiles:
        recs = list(
            Recommendation.objects.filter(
                user_id=profile["user_id"], is_new=True
            )
            .select_related("cached_event")
            .order_by("rank")
        )
        if not recs:
            continue

        payload = {
            "user_id": profile["user_id"],
            "telegram_id": str(profile["tg_id"]),
            "language": profile["language"],
            "recommendations": [_serialize(r) for r in recs],
        }
        if _post(base_url, payload):
            notified += 1
            total_recs += len(recs)
        else:
            failed += 1

    stats = NotifyStats(len(profiles), notified, failed, total_recs)
    logger.info("notify_telegram_bot: %s", stats)
    return stats


def _serialize(rec: Recommendation) -> dict[str, Any]:
    e = rec.cached_event
    return {
        "rank": rec.rank,
        "score": rec.score,
        "event": {
            "id": e.id,
            "title": e.title_ru or e.title,
            "category": e.category,
            "date_start": e.date_start.isoformat() if e.date_start else None,
            "venue_name": e.venue_name,
            "city": e.city,
            "url": e.url,
            "image_url": e.image_url,
            "is_free": e.is_free,
            "price_from": _decimal_to_str(e.price_from),
            "price_to": _decimal_to_str(e.price_to),
            "currency": e.currency,
            "ticket_links": e.ticket_links or {},
        },
    }


def _decimal_to_str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _post(base_url: str, payload: dict[str, Any]) -> bool:
    url = urljoin(base_url.rstrip("/") + "/", "api/recommendations/")
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    secret = getattr(settings, "TG_SERVICE_SECRET", "") or ""
    if secret:
        headers["X-Service-Secret"] = secret

    timeout = getattr(settings, "TG_SERVICE_TIMEOUT", 10.0)
    retries = getattr(settings, "TG_SERVICE_RETRIES", 2)

    for attempt in range(retries + 1):
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    return True
                logger.warning("tg-service POST %s -> %s", url, resp.status)
        except HTTPError as exc:
            if exc.code < 500:
                logger.warning("tg-service POST %s rejected %s", url, exc.code)
                return False
            logger.warning("tg-service POST %s server error %s", url, exc.code)
        except (URLError, TimeoutError) as exc:
            logger.warning("tg-service unreachable: %s", exc)

        if attempt < retries:
            time.sleep(0.5 * (attempt + 1))
    return False
