from rest_framework import serializers


class DailyRefreshStatsSerializer(serializers.Serializer):
    fetched = serializers.IntegerField()
    users_processed = serializers.IntegerField()
    recommendations_created = serializers.IntegerField()
