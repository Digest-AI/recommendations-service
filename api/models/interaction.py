from django.db import models


class Interaction(models.Model):
    """A signal from a user about an event. Drives both ranking and the
    eventual ML training set.
    """

    class Kind(models.TextChoices):
        VIEW = "view", "View"
        CLICK = "click", "Click"
        SAVE = "save", "Save"
        TICKET_CLICK = "ticket_click", "Ticket click"
        DISMISS = "dismiss", "Dismiss"

    user_id = models.CharField(max_length=64, db_index=True)
    event_id = models.CharField(max_length=64, db_index=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "interactions"
        indexes = [
            models.Index(fields=["user_id", "created_at"]),
            models.Index(fields=["event_id", "kind"]),
        ]
        verbose_name = "Interaction"
        verbose_name_plural = "Interactions"

    def __str__(self) -> str:
        return f"{self.user_id} {self.kind} {self.event_id}"
