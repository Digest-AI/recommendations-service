from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import UserProfile
from api.serializers import UserProfileSerializer
from utils.exceptions import BadRequest, NotFound, errors


class UserProfileView(APIView):
    """GET / PUT /api/profiles/<user_id>/ — manage a user's preferences."""

    @extend_schema(
        responses={200: UserProfileSerializer, **errors(NotFound)},
        operation_id="get_user_profile",
    )
    def get(self, request: Request, user_id: str) -> Response:
        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist as exc:
            raise NotFound(detail="profile_not_found", attr="user_id") from exc
        return Response(UserProfileSerializer(profile).data)

    @extend_schema(
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer, **errors(BadRequest)},
        operation_id="upsert_user_profile",
    )
    def put(self, request: Request, user_id: str) -> Response:
        profile, _ = UserProfile.objects.get_or_create(user_id=user_id)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=user_id)
        return Response(serializer.data, status=status.HTTP_200_OK)
