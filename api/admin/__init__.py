from django.contrib import admin

from api.models import (
    CachedEvent,
    Interaction,
    Recommendation,
    RecommendationLog,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user_id", "home_city", "language", "free_only", "max_price", "updated_at")
    search_fields = ("user_id", "home_city")
    list_filter = ("language", "free_only")


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ("user_id", "event_id", "kind", "created_at")
    search_fields = ("user_id", "event_id")
    list_filter = ("kind",)
    date_hierarchy = "created_at"


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = ("user_id", "event_id", "rank", "score", "served_at")
    search_fields = ("user_id", "event_id")
    list_filter = ("rank",)
    date_hierarchy = "served_at"


@admin.register(CachedEvent)
class CachedEventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "city", "date_start", "is_free", "fetched_at")
    search_fields = ("id", "title", "venue_name", "city")
    list_filter = ("category", "source", "is_free")
    date_hierarchy = "date_start"


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("user_id", "cached_event", "rank", "score", "is_new", "created_at")
    search_fields = ("user_id", "cached_event__id", "cached_event__title")
    list_filter = ("is_new",)
    date_hierarchy = "created_at"
