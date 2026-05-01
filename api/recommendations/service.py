from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from api.models import Recommendation, UserProfile
from api.parser import ParserClient

from .diversity import mmr_rerank
from .scoring import ContentScorer, UserContext

logger = logging.getLogger(__name__)


@dataclass
class RefreshStats:
    fetched: int
    users_processed: int
    recommendations_created: int


def run_daily_refresh() -> RefreshStats:
    base_url = (getattr(settings, "EVENTS_API_BASE_URL", "") or "").strip()
    if not base_url:
        raise RuntimeError("EVENTS_API_BASE_URL must be set")

    scrape_date = timezone.now().date().isoformat()
    client = ParserClient(base_url=base_url)
    candidates = client.fetch_scraped_on(scrape_date)
    logger.info("refresh: scraped-on date=%s fetched=%d events", scrape_date, len(candidates))

    user_ids = list(UserProfile.objects.values_list("user_id", flat=True))
    if not user_ids:
        return RefreshStats(len(candidates), 0, 0)

    if not candidates:
        return RefreshStats(0, len(user_ids), 0)

    existing_by_user: dict[str, set[int]] = defaultdict(set)
    for uid, eid in Recommendation.objects.filter(user_id__in=user_ids).values_list(
        "user_id", "event_id"
    ):
        existing_by_user[str(uid)].add(int(eid))

    scorer = ContentScorer(now=timezone.now())
    diversity_lambda = 0.7
    max_per_user = max(1, int(getattr(settings, "RECOMMENDATION_MAX_PER_USER", 40)))
    min_store = float(getattr(settings, "RECOMMENDATION_MIN_SCORE_TO_STORE", 0.06))
    rows: list[Recommendation] = []

    for uid in user_ids:
        uid_str = str(uid)
        ctx = UserContext.build(uid_str, client.fetch_rankable_detail)
        pool = list(candidates)
        if ctx.profile and ctx.profile.free_only:
            pool = [c for c in pool if c.is_free]
        pool = [c for c in pool if c.id not in ctx.seen_event_ids]
        if not pool:
            continue

        scored = [scorer.score(e, ctx) for e in pool]
        ranked = mmr_rerank(scored, top_k=len(scored), lambda_=diversity_lambda)

        already = existing_by_user[uid_str]
        ranked_new = [item for item in ranked if item.event.id not in already]
        if min_store > 0:
            ranked_new = [item for item in ranked_new if item.score >= min_store]
        ranked_new = ranked_new[:max_per_user]
        if not ranked_new:
            continue

        for rank, item in enumerate(ranked_new, start=1):
            rows.append(
                Recommendation(
                    user_id=uid_str,
                    event_id=item.event.id,
                    rank=rank,
                    score=round(float(item.score), 2),
                    feature_breakdown=item.breakdown,
                    is_new=True,
                )
            )
            already.add(item.event.id)

    if rows:
        Recommendation.objects.bulk_create(rows)

    return RefreshStats(len(candidates), len(user_ids), len(rows))
