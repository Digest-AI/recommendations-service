from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import InteractionSerializer
from utils.auth import BearerUserServiceAuthentication, IsAuthenticatedUserService
from utils.exceptions import BadRequest, Forbidden, errors


class InteractionsView(APIView):
    """POST /api/interactions/ — record a user signal (view/click/save/...)."""

    authentication_classes = [BearerUserServiceAuthentication]
    permission_classes = [IsAuthenticatedUserService]

    @extend_schema(
        request=InteractionSerializer,
        responses={201: InteractionSerializer, **errors(BadRequest, Forbidden)},
        operation_id="record_interaction",
    )
    def post(self, request: Request) -> Response:
        data = dict(request.data)
        # Always pin the interaction to the authenticated user.
        data["user_id"] = request.user.user_id
        serializer = InteractionSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
