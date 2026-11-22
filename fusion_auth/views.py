"""Session endpoints.

Not an identity provider: login forwards to Fusion_System_Administrator and
stores only the returned token, in an httpOnly cookie. This is the *user*
login — one door for every module. Operators sign in at the sysadmin console's
own URL; the two share an identity service, not a login page.
"""
import hashlib

from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from core.api import csrf
from core.api.exceptions import AuthenticationFailedError as AuthFailed
from core.api.exceptions import DomainError
from core.observability.middleware import get_request_id
from fusion_auth.client import IamThrottled, IamUnavailable, get_client
from fusion_auth.serializers import LoginSerializer, OkSerializer, RoleSerializer, SessionSerializer
from modules.accesscontrol import contracts as accesscontrol

COOKIE_MAX_AGE = 12 * 60 * 60
ACTIVE_ROLE_CACHE_TTL = COOKIE_MAX_AGE


def _active_role_cache_key(request):
    """Bind the UI role preference to the opaque IAM session, never its raw token."""
    token = request.auth or ""
    digest = hashlib.sha256(str(token).encode()).hexdigest()
    return f"fusion:active-role:{digest}"


def _set_cookie(response, token):
    response.set_cookie(
        settings.IAM_AUTH_COOKIE_NAME, token,
        max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax",
        secure=not settings.DEBUG, path="/",
    )
    return response


@extend_schema(request=LoginSerializer, responses=OkSerializer,
               description="Sets the httpOnly session cookie. The token "
                           "itself is never returned in the body.")
class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            raise DomainError("Username and password are required.",
                              code="missing_credentials")
        try:
            # NUM_PROXIES-aware, so a caller cannot pick the address the IAM throttles.
            token = get_client().login(username, password,
                                       client_ip=BaseThrottle().get_ident(request))
        except IamThrottled as exc:
            return _too_many_attempts(exc)
        except IamUnavailable as exc:
            return Response(
                {"error": {"code": "iam_unavailable",
                           "message": f"Identity service unavailable: {exc}",
                           "details": [], "request_id": ""}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not token:
            # One message for both modes (no enumeration), and 401 so alerting sees it.
            raise AuthFailed("Incorrect username or password.",
                             code="invalid_credentials")
        # The client holds this in memory and echoes it on every write.
        return _set_cookie(
            Response({"ok": True, "csrf_token": csrf.token_for(token)}), token)


def _too_many_attempts(exc: IamThrottled) -> Response:
    # A rate limit says when to come back; a locked account keeps the IAM's own words.
    if exc.retry_after:
        message = f"Too many sign-in attempts. Try again in {exc.retry_after} seconds."
    else:
        message = exc.message or "Too many sign-in attempts. Try again in a minute."
    response = Response(
        {"error": {"code": "too_many_attempts", "message": message,
                   "details": [], "request_id": get_request_id()}},
        status=status.HTTP_429_TOO_MANY_REQUESTS)
    if exc.retry_after:
        response["Retry-After"] = str(exc.retry_after)
    return response


@extend_schema(request=None, responses=OkSerializer)
class LogoutView(APIView):
    def post(self, request):
        token = request.COOKIES.get(settings.IAM_AUTH_COOKIE_NAME)
        if token:
            get_client().logout(token)
        response = Response({"ok": True})
        response.delete_cookie(settings.IAM_AUTH_COOKIE_NAME, path="/")
        return response


@extend_schema(responses=SessionSerializer)
class MeView(APIView):
    """The session payload the shell renders its sidebar from. `navigation`
    arrives already filtered, so the client cannot draw an ungranted module."""

    def get(self, request):
        p = request.principal
        active_role = cache.get(_active_role_cache_key(request), p.active_role)
        if active_role not in p.roles:
            active_role = p.active_role
        return Response({
            "user": {
                "id": p.user_id,
                "username": p.username,
                "display_name": p.display_name,
                "kind": p.kind,
                "email": p.email,
            },
            "active_role": active_role,
            "roles": list(p.roles),
            "permissions": sorted(p.permissions),
            "modules": list(p.modules),
            # The IAM's sidebar spans every app; fall back if it has not published.
            "navigation": list(p.navigation) or accesscontrol.build_navigation(
                granted_module_codes=p.modules,
                permissions=p.permissions,
            ),
            # Re-issued on every /me so a reloaded tab needs no second trip.
            "csrf_token": csrf.token_for(request.auth or ""),
        })

    @extend_schema(request=RoleSerializer, responses=SessionSerializer)
    def patch(self, request):
        """Switch which designation the sidebar and screens present them as."""
        role = (request.data.get("active_role") or "").strip()
        if not role or role not in request.principal.roles:
            raise DomainError("Choose one of your assigned roles.", code="unknown_role")
        # IAM versions that expose session read-only do not support PATCH /me.
        # This preference only affects the current platform session; IAM remains
        # authoritative for the user's roles, module grants, and permissions.
        cache.set(_active_role_cache_key(request), role, ACTIVE_ROLE_CACHE_TTL)
        return self.get(request)
