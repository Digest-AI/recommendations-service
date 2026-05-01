from django.db import models


class CachedEvent(models.Model):
    """Slim local copy of an event fetched from the parser service.

    Refreshed daily by the 3am scheduler job. Drops descriptions, raw
    categories and locale-specific fields the frontend doesn't render.
    Primary key is the parser-side id so that `Recommendation` can
    reference it directly.
    """

    id = models.CharField(max_length=64, primary_key=True)
    source = models.CharField(max_length=32)
    url = models.URLField(max_length=1024, blank=True, default="")
    title = models.CharField(max_length=512)
    title_ru = models.CharField(max_length=512, blank=True, default="")
    category = models.CharField(max_length=32)
    date_start = models.DateTimeField(null=True, blank=True, db_index=True)
    date_end = models.DateTimeField(null=True, blank=True)
    venue_name = models.CharField(max_length=256, blank=True, default="")
    city = models.CharField(max_length=128, blank=True, default="")
    price_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_to = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="MDL")
    is_free = models.BooleanField(default=False)
    image_url = models.URLField(max_length=1024, blank=True, default="")
    ticket_links = models.JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cached_events"
        verbose_name = "Cached Event"
        verbose_name_plural = "Cached Events"

    def __str__(self) -> str:
        return f"{self.id} {self.title}"
