from rest_framework import serializers

from api.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "user_id",
            "tg_id",
            "preferred_categories",
            "preferred_raw_categories",
            "home_city",
            "language",
            "max_price",
            "free_only",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
