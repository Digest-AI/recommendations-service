from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from api.recommendations.types import RankableEvent


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


def _category_slugs(item: dict[str, Any]) -> tuple[str, ...]:
    cats = item.get("categories") or []
    slugs: list[str] = []
    for c in cats:
        if isinstance(c, dict) and c.get("slug"):
            slugs.append(str(c["slug"]))
    return tuple(slugs)


def rankable_from_parser_payload(item: dict[str, Any]) -> RankableEvent | None:
    raw_id = item.get("id")
    try:
        ev_id = int(raw_id)
    except (TypeError, ValueError):
        return None

    slugs = _category_slugs(item)
    primary = slugs[0] if slugs else "other"
    provider = item.get("provider") or {}
    source = str(provider.get("slug") or "") if isinstance(provider, dict) else ""

    price_from = _parse_decimal(item.get("price_from"))
    price_to = _parse_decimal(item.get("price_to"))
    is_free = price_from is None or price_from == 0
    if price_to is not None and price_to == 0 and price_from is None:
        is_free = True

    return RankableEvent(
        id=ev_id,
        category=primary,
        raw_categories=slugs,
        source=source,
        venue_name=str(item.get("place") or ""),
        city=str(item.get("city") or ""),
        date_start=_parse_dt(item.get("date_start")),
        price_from=price_from,
        is_free=is_free,
    )
