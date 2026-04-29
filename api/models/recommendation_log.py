from django.db import models


class RecommendationLog(models.Model):
    """Records every recommendation served. Required to train Phase 2.

    Pair with Interaction (joined by user_id+event_id within served_at..N) to
    compute click-through rate and build (features → label) pairs.
    """

    user_id = models.CharField(max_length=64, db_index=True)
    event_id = models.CharField(max_length=64, db_index=True)
    rank = models.PositiveSmallIntegerField()
    score = models.FloatField()
    feature_breakdown = models.JSONField(default=dict, blank=True)
    served_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "recommendation_logs"
        indexes = [
            models.Index(fields=["user_id", "served_at"]),
        ]
        verbose_name = "Recommendation log"
        verbose_name_plural = "Recommendation logs"

    def __str__(self) -> str:
        return f"#{self.rank} {self.event_id} -> {self.user_id} ({self.score:.3f})"
