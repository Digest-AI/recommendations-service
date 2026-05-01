from rest_framework import serializers

from api.models import Recommendation

from .cached_event import CachedEventSerializer


class RecommendationSerializer(serializers.ModelSerializer):
    event = CachedEventSerializer(source="cached_event", read_only=True)
    is_new = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recommendation
        fields = ["rank", "score", "is_new", "event", "created_at"]
        read_only_fields = fields


class RecommendationQuerySerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
