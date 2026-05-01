from django.db import models


class Recommendation(models.Model):
    """Pre-computed recommendation served to a user.

    Created in bulk by the daily 3am scheduler job. `is_new=True` means
    the user hasn't fetched this rec yet via the frontend endpoint —
    that endpoint flips the flag to False on read. The TG bot endpoint
    reads new ones without flipping.
    """

    user_id = models.CharField(max_length=64, db_index=True)
    cached_event = models.ForeignKey(
        "api.CachedEvent",
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    is_new = models.BooleanField(default=True)
    rank = models.PositiveSmallIntegerField()
    score = models.FloatField()
    feature_breakdown = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendations"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "cached_event"],
                name="recommendation_unique_user_event",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "is_new"]),
            models.Index(fields=["user_id", "created_at"]),
        ]
        verbose_name = "Recommendation"
        verbose_name_plural = "Recommendations"

    def __str__(self) -> str:
        return f"#{self.rank} {self.cached_event_id} -> {self.user_id}"
