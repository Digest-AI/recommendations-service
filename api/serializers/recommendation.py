from rest_framework import serializers

from api.models import Recommendation


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = ["rank", "score", "is_new", "event_id"]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("score") is not None:
            data["score"] = round(float(data["score"]), 2)
        if self.context.get("include_public_id"):
            data["public_id"] = instance.user_id
        return data


class RecommendationQuerySerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)


class NewRecommendationQuerySerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False, allow_blank=True, default="")
