from django.db import models


class Recommendation(models.Model):
    """Ranked suggestion for a user (parser numeric ``event_id`` only — no local event cache)."""

    user_id = models.CharField(max_length=64, db_index=True)
    event_id = models.BigIntegerField(db_index=True)
    is_new = models.BooleanField(default=True)
    rank = models.PositiveSmallIntegerField()
    score = models.FloatField()
    feature_breakdown = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendations"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "event_id"],
                name="recommendation_unique_user_event_id",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "is_new"], name="rec_user_new_idx"),
            models.Index(fields=["user_id", "created_at"], name="rec_user_created_idx"),
        ]
        verbose_name = "Recommendation"
        verbose_name_plural = "Recommendations"

    def __str__(self) -> str:
        return f"#{self.rank} event={self.event_id} -> {self.user_id}"
