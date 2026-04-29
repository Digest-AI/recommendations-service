from rest_framework import serializers

from .event import EventSerializer


class RecommendationSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    score = serializers.FloatField()
    feature_breakdown = serializers.DictField(child=serializers.FloatField())
    event = EventSerializer()


class RecommendationQuerySerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    limit = serializers.IntegerField(required=False, default=10, min_value=1, max_value=50)
    diversity = serializers.FloatField(required=False, default=0.7, min_value=0.0, max_value=1.0)
    exclude_seen = serializers.BooleanField(required=False, default=True)
