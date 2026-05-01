from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Recommendation
from api.recommendations.policy import apply_api_score_floor
from api.serializers import (
    NewRecommendationQuerySerializer,
    RecommendationQuerySerializer,
    RecommendationSerializer,
)
from utils.exceptions import BadRequest, errors
from utils.transformers import pythonize


def _validate_user_id(request: Request) -> str:
    query = RecommendationQuerySerializer(data=pythonize(request.query_params.dict()))
    query.is_valid(raise_exception=True)
    return query.validated_data["user_id"]


class RecommendationsView(APIView):
    """GET /api/recommendations/?userId=...

    Rows below ``RECOMMENDATION_MIN_SCORE_API`` stay in DB but are omitted here.
    Fields: ``rank``, ``score``, ``is_new``, ``event_id``.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[RecommendationQuerySerializer],
        responses={200: RecommendationSerializer(many=True), **errors(BadRequest)},
        operation_id="list_recommendations",
    )
    def get(self, request: Request) -> Response:
        user_id = _validate_user_id(request)

        qs = apply_api_score_floor(
            Recommendation.objects.filter(user_id=user_id).order_by(
                "-is_new", "-created_at", "rank"
            )
        )
        items = list(qs)
        payload = RecommendationSerializer(items, many=True).data

        return Response(payload, status=status.HTTP_200_OK)


class NewRecommendationsView(APIView):
    """GET /api/recommendations/new/[?userId=]

    Only ``is_new=True``, same score floor as the main recommendations list.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[NewRecommendationQuerySerializer],
        responses={
            200: RecommendationSerializer(many=True),
            **errors(BadRequest),
        },
        operation_id="list_new_recommendations",
    )
    def get(self, request: Request) -> Response:
        query = NewRecommendationQuerySerializer(data=pythonize(request.query_params.dict()))
        query.is_valid(raise_exception=True)
        raw_uid = (query.validated_data.get("user_id") or "").strip()

        qs = Recommendation.objects.filter(is_new=True)
        if raw_uid:
            qs = qs.filter(user_id=raw_uid)
        qs = apply_api_score_floor(qs.order_by("user_id", "-created_at", "rank"))

        payload = RecommendationSerializer(list(qs), many=True).data
        return Response(payload, status=status.HTTP_200_OK)
