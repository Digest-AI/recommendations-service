from django.urls import path

from api.views import InteractionsView, RecommendationsView, UserProfileView

urlpatterns = [
    path("recommendations/", RecommendationsView.as_view(), name="recommendations"),
    path("interactions/", InteractionsView.as_view(), name="interactions"),
    path("profiles/<str:user_id>/", UserProfileView.as_view(), name="user-profile"),
]
