import hmac

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Recommendation
from api.serializers import RecommendationQuerySerializer, RecommendationSerializer
from utils.auth import BearerUserServiceAuthentication, IsAuthenticatedUserService
from utils.exceptions import BadRequest, Forbidden, errors
from utils.transformers import pythonize


def _validate_user_id(request: Request) -> str:
    query = RecommendationQuerySerializer(data=pythonize(request.query_params.dict()))
    query.is_valid(raise_exception=True)
    return query.validated_data["user_id"]


class RecommendationsView(APIView):
    """GET /api/recommendations/?userId=...

    Frontend endpoint. Returns ALL recommendations for the authenticated
    user (new + old), then flips `is_new=True` rows to False so the next
    call only sees fresh ones as new.

    Authentication: `Authorization: Bearer <accessToken>` validated
    against the user service. The supplied `userId` must match the
    authenticated user's `publicId`.
    """

    authentication_classes = [BearerUserServiceAuthentication]
    permission_classes = [IsAuthenticatedUserService]

    @extend_schema(
        parameters=[RecommendationQuerySerializer],
        responses={200: RecommendationSerializer(many=True), **errors(BadRequest, Forbidden)},
        operation_id="list_recommendations",
    )
    def get(self, request: Request) -> Response:
        user_id = _validate_user_id(request)
        if user_id != getattr(request.user, "user_id", None):
            raise Forbidden(detail="user_mismatch", attr="userId")

        qs = (
            Recommendation.objects.filter(user_id=user_id)
            .select_related("cached_event")
            .order_by("-is_new", "-created_at", "rank")
        )
        items = list(qs)
        payload = RecommendationSerializer(items, many=True).data

        new_ids = [r.id for r in items if r.is_new]
        if new_ids:
            Recommendation.objects.filter(id__in=new_ids).update(is_new=False)

        return Response(payload, status=status.HTTP_200_OK)


class NewRecommendationsView(APIView):
    """GET /api/recommendations/new/?userId=...

    Service-to-service endpoint for the TG bot. Returns only the user's
    `is_new=True` recommendations and does NOT flip the flag.

    Authentication: header `X-Service-Secret` must match SERVICE_SECRET
    (constant-time compared).
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[RecommendationQuerySerializer],
        responses={
            200: RecommendationSerializer(many=True),
            **errors(BadRequest, Forbidden),
        },
        operation_id="list_new_recommendations",
    )
    def get(self, request: Request) -> Response:
        secret = request.headers.get("X-Service-Secret") or ""
        expected = settings.SERVICE_SECRET or ""
        if not expected or not hmac.compare_digest(secret, expected):
            raise Forbidden(detail="invalid_service_secret", attr="X-Service-Secret")

        user_id = _validate_user_id(request)
        qs = (
            Recommendation.objects.filter(user_id=user_id, is_new=True)
            .select_related("cached_event")
            .order_by("-created_at", "rank")
        )
        payload = RecommendationSerializer(list(qs), many=True).data
        return Response(payload, status=status.HTTP_200_OK)
