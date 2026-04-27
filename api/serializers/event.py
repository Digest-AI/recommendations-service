from rest_framework import serializers


class EventSerializer(serializers.Serializer):
    id = serializers.CharField()
    source = serializers.CharField()
    url = serializers.URLField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    category = serializers.CharField()
    raw_categories = serializers.ListField(child=serializers.CharField())
    date_start = serializers.DateTimeField(allow_null=True)
    date_end = serializers.DateTimeField(allow_null=True)
    venue_name = serializers.CharField(allow_blank=True)
    venue_address = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    price_to = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    currency = serializers.CharField()
    is_free = serializers.BooleanField()
    image_url = serializers.URLField(allow_blank=True)
    ticket_links = serializers.DictField(child=serializers.CharField())
