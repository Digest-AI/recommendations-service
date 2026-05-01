from django.urls import path

from api.views import (
    DailyRefreshTriggerView,
    InteractionsView,
    NewRecommendationsView,
    RecommendationsView,
    UserProfileCollectionView,
    UserProfileView,
)

urlpatterns = [
    path(
        "jobs/daily-refresh/",
        DailyRefreshTriggerView.as_view(),
        name="daily-refresh-trigger",
    ),
    path("recommendations/", RecommendationsView.as_view(), name="recommendations"),
    path("recommendations/new/", NewRecommendationsView.as_view(), name="recommendations-new"),
    path("interactions/", InteractionsView.as_view(), name="interactions"),
    path("profiles/", UserProfileCollectionView.as_view(), name="user-profiles"),
    path("profiles/<str:user_id>/", UserProfileView.as_view(), name="user-profile"),
]
