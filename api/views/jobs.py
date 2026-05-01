from __future__ import annotations

from dataclasses import asdict

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.recommendations.service import run_daily_refresh
from api.serializers.jobs import DailyRefreshStatsSerializer
from utils.exceptions import Forbidden, InternalServerError, errors


class DailyRefreshTriggerView(APIView):
    """POST /api/jobs/daily-refresh/

    Fetches today's scraped events from the parser ``/api/events/scraped-on/``,
    rebuilds recommendations per user profile (numeric ``event_id`` only).
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={
            200: DailyRefreshStatsSerializer,
            **errors(Forbidden, InternalServerError),
        },
        operation_id="trigger_daily_refresh",
    )
    def post(self, request: Request) -> Response:
        try:
            stats = run_daily_refresh()
        except RuntimeError as exc:
            raise InternalServerError(detail=str(exc)) from exc
        return Response(asdict(stats))
