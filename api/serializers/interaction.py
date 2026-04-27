from rest_framework import serializers

from api.models import Interaction


class InteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = ["id", "user_id", "event_id", "kind", "created_at"]
        read_only_fields = ["id", "created_at"]
