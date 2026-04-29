from dataclasses import asdict

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.recommendations.engine import RecommendationEngine, RecommendationRequest
from api.serializers import RecommendationQuerySerializer, RecommendationSerializer
from utils.exceptions import BadRequest, errors
from utils.transformers import pythonize


class RecommendationsView(APIView):
    """GET /api/recommendations/?userId=...&limit=10"""

    @extend_schema(
        parameters=[RecommendationQuerySerializer],
        responses={200: RecommendationSerializer(many=True), **errors(BadRequest)},
        operation_id="list_recommendations",
    )
    def get(self, request: Request) -> Response:
        query = RecommendationQuerySerializer(data=pythonize(request.query_params.dict()))
        query.is_valid(raise_exception=True)
        params = query.validated_data

        engine = RecommendationEngine()
        ranked = engine.recommend(
            RecommendationRequest(
                user_id=params["user_id"],
                limit=params["limit"],
                diversity=params["diversity"],
                exclude_seen=params["exclude_seen"],
            )
        )

        payload = [
            {
                "rank": position,
                "score": item.score,
                "feature_breakdown": item.breakdown,
                "event": _event_to_dict(item.event),
            }
            for position, item in enumerate(ranked, start=1)
        ]
        return Response(payload, status=status.HTTP_200_OK)


def _event_to_dict(event) -> dict:
    data = asdict(event)
    data["raw_categories"] = list(event.raw_categories)
    return data
