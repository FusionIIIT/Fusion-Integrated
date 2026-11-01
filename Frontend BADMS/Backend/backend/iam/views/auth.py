from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from iam.authentication import COOKIE_NAME, IamTokenAuthentication
from iam import services
from iam.models import IamUser
from iam.services import Locked, authenticate, build_session

TOKEN_TTL_HOURS = 12


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")


class LoginView(APIView):
    """POST /api/iam/v1/auth/login  {username, password}

    Authenticates an ERP user. This is NOT the operator console login — that
    stays at /api/login/ against its own account pool.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"detail": "Username and password are required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            token = authenticate(username, password, ip=_client_ip(request))
        except Locked as exc:
            msg = ("Too many failed attempts. Contact the office to unlock."
                   if exc.minutes is None
                   else f"Too many failed attempts. Try again in {exc.minutes} minute(s).")
            return Response({"detail": msg}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if token is None:
            # One message for every failure mode — no user enumeration.
            return Response({"detail": "Incorrect username or password."},
                            status=status.HTTP_401_UNAUTHORIZED)

        # The raw value exists here and in the holder's cookie, nowhere else.
        response = Response({"token": token.raw_key,
                             "expires_at": token.expires_at.isoformat()})
        response.set_cookie(
            COOKIE_NAME, token.raw_key, max_age=TOKEN_TTL_HOURS * 3600,
            httponly=True, samesite="Lax", secure=not settings.DEBUG, path="/",
        )
        return response


class LogoutView(APIView):
    authentication_classes = [IamTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.token.revoke()
        response = Response({"detail": "Signed out."})
        response.delete_cookie(COOKIE_NAME, path="/")
        return response


class MeView(APIView):
    """GET /api/iam/v1/me — identity, roles, permissions and module grants."""

    authentication_classes = [IamTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = build_session(request.user.token)
        if not payload:
            return Response({"detail": "User no longer exists."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(payload)

    def patch(self, request):
        """Remember which designation they chose to work as."""
        role = (request.data.get("last_selected_role") or "").strip()
        token = request.user.token
        user = IamUser.objects.filter(erp_user_id=token.erp_user_id).first()
        if user is None:
            return Response({"detail": "User no longer exists."},
                            status=status.HTTP_404_NOT_FOUND)

        roles = services.designations_for(user.erp_user_id)
        if user.kind not in roles:
            roles = [user.kind, *roles]
        if role and role not in roles:
            # A role they do not hold would vanish on the next read, looking broken.
            return Response({"detail": f"You do not hold the role {role!r}."},
                            status=status.HTTP_400_BAD_REQUEST)

        user.last_selected_role = role
        user.save(update_fields=["last_selected_role"])
        return Response(build_session(token))
