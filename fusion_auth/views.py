"""Session endpoints.

Not an identity provider: login forwards to Fusion_System_Administrator and
stores only the returned token, in an httpOnly cookie. This is the *user*
login — one door for every module. Operators sign in at the sysadmin console's
own URL; the two share an identity service, not a login page.
"""
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csrf
from core.api.exceptions import AuthenticationFailedError as AuthFailed
from core.api.exceptions import DomainError
from fusion_auth.client import IamUnavailable, get_client
from fusion_auth.serializers import LoginSerializer, OkSerializer, SessionSerializer
from modules.accesscontrol import contracts as accesscontrol

COOKIE_MAX_AGE = 12 * 60 * 60


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
            token = get_client().login(username, password)
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
        return Response({
            "user": {
                "id": p.user_id,
                "username": p.username,
                "display_name": p.display_name,
                "kind": p.kind,
                "email": p.email,
            },
            "active_role": p.active_role,
            "roles": list(p.roles),
            "permissions": sorted(p.permissions),
            "modules": list(p.modules),
            "navigation": accesscontrol.build_navigation(
                granted_module_codes=p.modules,
                permissions=p.permissions,
            ),
            # Re-issued on every /me so a reloaded tab needs no second trip.
            "csrf_token": csrf.token_for(request.auth or ""),
        })
