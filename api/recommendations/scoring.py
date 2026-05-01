from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from api.models import Interaction, UserProfile

from .types import RankableEvent


@dataclass(frozen=True)
class ScoredEvent:
    event: RankableEvent
    score: float
    breakdown: dict[str, float]


@dataclass(frozen=True)
class UserContext:
    """Everything the scorer needs about a user. Built once per request."""

    profile: UserProfile | None
    seen_event_ids: set[int]
    venue_affinity: dict[str, int]
    source_affinity: dict[str, int]
    category_affinity: dict[str, int]

    @classmethod
    def build(cls, user_id: str, fetch_rankable) -> UserContext:
        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            profile = None

        recent = list(
            Interaction.objects.filter(user_id=user_id)
            .order_by("-created_at")
            .values("event_id", "kind")[:200]
        )

        seen: set[int] = set()
        venue_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        category_counts: Counter[str] = Counter()

        positive_kinds = {
            Interaction.Kind.CLICK,
            Interaction.Kind.SAVE,
            Interaction.Kind.TICKET_CLICK,
        }

        for row in recent:
            try:
                eid = int(row["event_id"])
            except (TypeError, ValueError):
                continue
            seen.add(eid)
            if row["kind"] not in positive_kinds:
                continue
            event = fetch_rankable(eid)
            if event is None:
                continue
            if event.venue_name:
                venue_counts[event.venue_name] += 1
            if event.source:
                source_counts[event.source] += 1
            category_counts[event.category] += 1

        return cls(
            profile=profile,
            seen_event_ids=seen,
            venue_affinity=dict(venue_counts),
            source_affinity=dict(source_counts),
            category_affinity=dict(category_counts),
        )


class ContentScorer:
    """Hand-tuned linear model: ``score`` is a weighted sum of features in [0, 1], not P(click)."""

    weights = {
        "category_match": 0.30,
        "raw_category_overlap": 0.20,
        "city_match": 0.10,
        "price_fit": 0.10,
        "recency": 0.10,
        "venue_affinity": 0.10,
        "source_affinity": 0.05,
        "category_affinity": 0.05,
    }

    def __init__(self, now: datetime | None = None):
        self._now = now or datetime.now(timezone.utc)

    def score(self, event: RankableEvent, ctx: UserContext) -> ScoredEvent:
        features = {
            "category_match": self._category_match(event, ctx),
            "raw_category_overlap": self._raw_overlap(event, ctx),
            "city_match": self._city_match(event, ctx),
            "price_fit": self._price_fit(event, ctx),
            "recency": self._recency(event),
            "venue_affinity": self._venue_affinity(event, ctx),
            "source_affinity": self._source_affinity(event, ctx),
            "category_affinity": self._category_affinity(event, ctx),
        }
        total = sum(self.weights[name] * value for name, value in features.items())
        return ScoredEvent(event=event, score=total, breakdown=features)

    def _category_match(self, event: RankableEvent, ctx: UserContext) -> float:
        if ctx.profile is None:
            return 0.0
        prefs = set(ctx.profile.preferred_categories or [])
        return 1.0 if event.category in prefs else 0.0

    def _raw_overlap(self, event: RankableEvent, ctx: UserContext) -> float:
        if ctx.profile is None:
            return 0.0
        prefs = {tag.lower() for tag in (ctx.profile.preferred_raw_categories or [])}
        if not prefs:
            return 0.0
        event_tags = {tag.lower() for tag in event.raw_categories}
        if not event_tags:
            return 0.0
        intersection = prefs & event_tags
        union = prefs | event_tags
        return len(intersection) / len(union)

    def _city_match(self, event: RankableEvent, ctx: UserContext) -> float:
        if ctx.profile is None or not event.city:
            return 0.0
        return 1.0 if event.city == ctx.profile.home_city else 0.0

    def _price_fit(self, event: RankableEvent, ctx: UserContext) -> float:
        if event.is_free:
            return 1.0
        if ctx.profile is None or ctx.profile.max_price is None:
            return 0.5
        if event.price_from is None:
            return 0.5
        budget: Decimal = ctx.profile.max_price
        if event.price_from <= budget:
            return 1.0
        overshoot = float((event.price_from - budget) / budget)
        return max(0.0, 1.0 - overshoot)

    def _recency(self, event: RankableEvent) -> float:
        if event.date_start is None:
            return 0.0
        days_until = (event.date_start - self._now).total_seconds() / 86400
        if days_until < 0:
            return 0.0
        return math.exp(-days_until / 14.0)

    def _venue_affinity(self, event: RankableEvent, ctx: UserContext) -> float:
        if not event.venue_name or not ctx.venue_affinity:
            return 0.0
        count = ctx.venue_affinity.get(event.venue_name, 0)
        return min(1.0, math.log1p(count) / math.log(5))

    def _source_affinity(self, event: RankableEvent, ctx: UserContext) -> float:
        if not ctx.source_affinity:
            return 0.0
        total = sum(ctx.source_affinity.values()) or 1
        return ctx.source_affinity.get(event.source, 0) / total

    def _category_affinity(self, event: RankableEvent, ctx: UserContext) -> float:
        if not ctx.category_affinity:
            return 0.0
        total = sum(ctx.category_affinity.values()) or 1
        return ctx.category_affinity.get(event.category, 0) / total
