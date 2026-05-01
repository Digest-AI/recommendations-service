from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Interaction, Recommendation, RecommendationLog, UserProfile
from api.serializers import UserProfileSerializer
from utils.auth import BearerUserServiceAuthentication, IsAuthenticatedUserService
from utils.exceptions import BadRequest, Forbidden, NotFound, errors
from utils.exceptions.classes import APIException


class _Conflict(APIException):
    status_code = 409
    default_detail = "conflict"
    default_code = "conflict"


def _require_self(request: Request, user_id: str) -> None:
    if user_id != getattr(request.user, "user_id", None):
        raise Forbidden(detail="user_mismatch", attr="user_id")


class UserProfileCollectionView(APIView):
    """POST /api/profiles/ — create a profile for the authenticated user."""

    authentication_classes = [BearerUserServiceAuthentication]
    permission_classes = [IsAuthenticatedUserService]

    @extend_schema(
        request=UserProfileSerializer,
        responses={201: UserProfileSerializer, **errors(BadRequest, Forbidden)},
        operation_id="create_user_profile",
    )
    def post(self, request: Request) -> Response:
        serializer = UserProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Always bind the new profile to the authenticated user — never
        # trust an arbitrary user_id from the request body.
        user_id = request.user.user_id
        if UserProfile.objects.filter(user_id=user_id).exists():
            raise _Conflict(detail="profile_already_exists", attr="user_id")
        serializer.save(user_id=user_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    """GET / PATCH / DELETE /api/profiles/<user_id>/."""

    authentication_classes = [BearerUserServiceAuthentication]
    permission_classes = [IsAuthenticatedUserService]

    @extend_schema(
        responses={200: UserProfileSerializer, **errors(Forbidden, NotFound)},
        operation_id="get_user_profile",
    )
    def get(self, request: Request, user_id: str) -> Response:
        _require_self(request, user_id)
        profile = self._get_or_404(user_id)
        return Response(UserProfileSerializer(profile).data)

    @extend_schema(
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer, **errors(BadRequest, Forbidden, NotFound)},
        operation_id="update_user_profile",
    )
    def patch(self, request: Request, user_id: str) -> Response:
        _require_self(request, user_id)
        profile = self._get_or_404(user_id)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=user_id)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={204: None, **errors(Forbidden, NotFound)},
        operation_id="delete_user_profile",
    )
    def delete(self, request: Request, user_id: str) -> Response:
        _require_self(request, user_id)
        profile = self._get_or_404(user_id)
        Recommendation.objects.filter(user_id=user_id).delete()
        Interaction.objects.filter(user_id=user_id).delete()
        RecommendationLog.objects.filter(user_id=user_id).delete()
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _get_or_404(user_id: str) -> UserProfile:
        try:
            return UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist as exc:
            raise NotFound(detail="profile_not_found", attr="user_id") from exc
