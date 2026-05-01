"""Filters for recommendation querysets (API visibility vs raw DB rows)."""

from __future__ import annotations

from django.conf import settings


def apply_api_score_floor(qs):
    """Hide weak linear-score rows from API responses (does not delete DB rows)."""
    floor = float(getattr(settings, "RECOMMENDATION_MIN_SCORE_API", 0.08))
    if floor <= 0:
        return qs
    return qs.filter(score__gte=floor)
