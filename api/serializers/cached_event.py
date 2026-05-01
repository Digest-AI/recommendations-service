from rest_framework import serializers

from api.models import CachedEvent


class CachedEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CachedEvent
        fields = [
            "id",
            "source",
            "url",
            "title",
            "title_ru",
            "category",
            "date_start",
            "date_end",
            "venue_name",
            "city",
            "price_from",
            "price_to",
            "currency",
            "is_free",
            "image_url",
            "ticket_links",
        ]
