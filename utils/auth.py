"""Bearer-token authentication backed by the user service.

Validates the inbound `Authorization: Bearer <token>` by calling
`GET /api/user/me` on the user service. On success, attaches the
external `publicId` to `request.user_id`. Successful validations are
cached briefly to avoid hammering the user service.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from rest_framework import authentication, exceptions

logger = logging.getLogger(__name__)

_CACHE_TTL = 60  # seconds


class _AuthedUser:
    """Lightweight stand-in for `request.user` carrying the external id."""

    is_authenticated = True

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"AuthedUser({self.user_id})"


class BearerUserServiceAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request) -> tuple[_AuthedUser, str] | None:
        header = authentication.get_authorization_header(request).decode("ascii", errors="ignore")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None
        token = parts[1]

        public_id = _resolve_public_id(token)
        if not public_id:
            raise exceptions.AuthenticationFailed("invalid_token")
        request.user_id = public_id
        return _AuthedUser(public_id), token

    def authenticate_header(self, request) -> str:
        return self.keyword


def _resolve_public_id(token: str) -> str | None:
    base_url = getattr(settings, "USER_SERVICE_BASE_URL", "")
    if not base_url:
        logger.error("USER_SERVICE_BASE_URL is not configured")
        return None

    cache_key = "auth:token:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None  # empty string sentinel = invalid

    url = base_url.rstrip("/") + "/api/user/me"
    req = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(req, timeout=getattr(settings, "USER_SERVICE_TIMEOUT", 5.0)) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 401:
            cache.set(cache_key, "", _CACHE_TTL)
        else:
            logger.warning("user-service /me HTTP %s", exc.code)
        return None
    except (URLError, TimeoutError, ValueError) as exc:
        logger.warning("user-service unreachable: %s", exc)
        return None

    public_id = data.get("publicId") or data.get("public_id")
    if not public_id:
        return None
    cache.set(cache_key, public_id, _CACHE_TTL)
    return str(public_id)


class IsAuthenticatedUserService:
    """DRF permission compatible — relies on `BearerUserServiceAuthentication`."""

    def has_permission(self, request, view) -> bool:
        return getattr(request.user, "is_authenticated", False)

    def has_object_permission(self, request, view, obj) -> bool:
        return self.has_permission(request, view)
