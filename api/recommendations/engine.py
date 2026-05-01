from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from api.dto import EventDTO, EventFilters
from api.gateways import get_event_gateway
from api.models import RecommendationLog

from .diversity import mmr_rerank
from .scoring import ContentScorer, ScoredEvent, UserContext


@dataclass(frozen=True)
class RecommendationRequest:
    user_id: str
    limit: int = 10
    diversity: float = 0.7
    exclude_seen: bool = True


class RecommendationEngine:
    """Glues gateway + scorer + diversity + logging."""

    def __init__(self) -> None:
        self._gateway = get_event_gateway()

    def recommend(self, request: RecommendationRequest) -> list[ScoredEvent]:
        ctx = UserContext.build(request.user_id, self._gateway.get)

        filters = self._filters_for(ctx)
        candidates = self._gateway.list(filters)
        ranked = self._rank(ctx, candidates, request.limit, request.diversity, request.exclude_seen)

        self._log(request.user_id, ranked)
        return ranked

    def score_for_user(
        self,
        user_id: str,
        candidates: list[EventDTO],
        limit: int,
        diversity: float = 0.7,
        exclude_seen: bool = True,
    ) -> list[ScoredEvent]:
        """Rank a pre-fetched candidate list for one user.

        Used by the daily 3am job: events are fetched once, then this is
        called per user. No gateway list() call, no logging.
        """
        ctx = UserContext.build(user_id, self._gateway.get)
        return self._rank(ctx, candidates, limit, diversity, exclude_seen)

    @staticmethod
    def _rank(
        ctx: UserContext,
        candidates: list[EventDTO],
        limit: int,
        diversity: float,
        exclude_seen: bool,
    ) -> list[ScoredEvent]:
        if exclude_seen and ctx.seen_event_ids:
            candidates = [e for e in candidates if e.id not in ctx.seen_event_ids]
        if not candidates:
            return []
        scorer = ContentScorer()
        scored = [scorer.score(event, ctx) for event in candidates]
        return mmr_rerank(scored, top_k=limit, lambda_=diversity)

    @staticmethod
    def _filters_for(ctx: UserContext) -> EventFilters:
        now = datetime.now(timezone.utc)
        if ctx.profile is None:
            return EventFilters(starts_after=now)
        return EventFilters(
            starts_after=now,
            free_only=ctx.profile.free_only,
        )

    @staticmethod
    def _log(user_id: str, ranked: list[ScoredEvent]) -> None:
        if not ranked:
            return
        RecommendationLog.objects.bulk_create(
            [
                RecommendationLog(
                    user_id=user_id,
                    event_id=item.event.id,
                    rank=position,
                    score=item.score,
                    feature_breakdown=item.breakdown,
                )
                for position, item in enumerate(ranked, start=1)
            ]
        )
