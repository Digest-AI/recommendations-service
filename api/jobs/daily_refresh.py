from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from django.conf import settings
from django.db import transaction

from api.dto import EventDTO, EventFilters
from api.gateways import get_event_gateway
from api.models import CachedEvent, Recommendation, UserProfile
from api.recommendations.engine import RecommendationEngine

logger = logging.getLogger(__name__)


@dataclass
class RefreshStats:
    fetched: int
    cached_upserts: int
    pruned_events: int
    users_processed: int
    recommendations_created: int


def daily_refresh() -> RefreshStats:
    """Daily job: fetch parser → cache events → bulk-create recs per user.

    Network and scoring run outside the DB transaction; only the final
    write phase is atomic.
    """

    today_midnight = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    gateway = get_event_gateway()
    candidates = gateway.list(EventFilters(starts_after=today_midnight))
    logger.info("daily_refresh: fetched %d events from parser", len(candidates))

    if not candidates:
        logger.warning("daily_refresh: parser returned no events; nothing to refresh")
        return RefreshStats(0, 0, 0, 0, 0)

    candidate_ids = {e.id for e in candidates}
    cached_rows = [_to_cached_event(e) for e in candidates]

    # Score per user OUTSIDE the transaction — this can fan out to the
    # gateway (e.g. detail lookups for past interactions) and we don't
    # want to hold a DB write lock while doing network I/O.
    engine = RecommendationEngine()
    limit = settings.DAILY_REC_LIMIT
    user_ids = list(UserProfile.objects.values_list("user_id", flat=True))

    new_rows: list[Recommendation] = []
    for user_id in user_ids:
        scored = engine.score_for_user(user_id, candidates, limit=limit)
        for rank, item in enumerate(scored, start=1):
            if item.event.id not in candidate_ids:
                continue
            new_rows.append(
                Recommendation(
                    user_id=user_id,
                    cached_event_id=item.event.id,
                    is_new=True,
                    rank=rank,
                    score=item.score,
                    feature_breakdown=item.breakdown,
                )
            )

    with transaction.atomic():
        pruned = _prune_past_events(today_midnight)
        cached_upserts = _upsert_cached_events(cached_rows)
        if new_rows:
            Recommendation.objects.bulk_create(new_rows, ignore_conflicts=True)

    stats = RefreshStats(
        fetched=len(candidates),
        cached_upserts=cached_upserts,
        pruned_events=pruned,
        users_processed=len(user_ids),
        recommendations_created=len(new_rows),
    )
    logger.info("daily_refresh: %s", stats)
    return stats


def _prune_past_events(threshold: datetime) -> int:
    """Drop events whose start date is in the past. Recommendations cascade."""
    deleted, _ = CachedEvent.objects.filter(date_start__lt=threshold).delete()
    return deleted


def _upsert_cached_events(rows: list[CachedEvent]) -> int:
    if not rows:
        return 0
    update_fields = [
        "source", "url", "title", "title_ru", "category",
        "date_start", "date_end", "venue_name", "city",
        "price_from", "price_to", "currency", "is_free",
        "image_url", "ticket_links",
    ]
    CachedEvent.objects.bulk_create(
        rows,
        update_conflicts=True,
        unique_fields=["id"],
        update_fields=update_fields,
    )
    return len(rows)


def _to_cached_event(e: EventDTO) -> CachedEvent:
    return CachedEvent(
        id=e.id,
        source=e.source,
        url=e.url,
        title=e.title,
        title_ru=e.title_ru,
        category=e.category,
        date_start=e.date_start,
        date_end=e.date_end,
        venue_name=e.venue_name,
        city=e.city,
        price_from=e.price_from,
        price_to=e.price_to,
        currency=e.currency,
        is_free=e.is_free,
        image_url=e.image_url,
        ticket_links=dict(e.ticket_links),
    )
