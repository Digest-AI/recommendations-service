from __future__ import annotations

from .scoring import ScoredEvent


def mmr_rerank(
    candidates: list[ScoredEvent],
    top_k: int,
    lambda_: float = 0.7,
) -> list[ScoredEvent]:
    if top_k <= 0 or not candidates:
        return []

    pool = sorted(candidates, key=lambda c: c.score, reverse=True)
    selected: list[ScoredEvent] = [pool.pop(0)]

    while pool and len(selected) < top_k:
        best_idx = 0
        best_value = float("-inf")
        for idx, cand in enumerate(pool):
            similarity = max(_similarity(cand, picked) for picked in selected)
            value = lambda_ * cand.score - (1 - lambda_) * similarity
            if value > best_value:
                best_value = value
                best_idx = idx
        selected.append(pool.pop(best_idx))

    return selected


def _similarity(a: ScoredEvent, b: ScoredEvent) -> float:
    score = 0.0
    if a.event.category == b.event.category:
        score += 0.5
    if a.event.venue_name and a.event.venue_name == b.event.venue_name:
        score += 0.3
    if a.event.source == b.event.source:
        score += 0.2
    return score
