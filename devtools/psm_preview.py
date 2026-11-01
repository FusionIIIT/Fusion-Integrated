import secrets

from django.conf import settings
from django.core import signing
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csrf
from devtools.psm_preview_auth import COOKIE, resolve_token
from modules.psm.models import Membership


def payload(principal, token):
    return {
        "user": {
            "id": principal.user_id,
            "username": principal.username,
            "display_name": principal.display_name,
            "kind": "staff",
        },
        "active_role": principal.active_role,
        "roles": list(principal.roles),
        "permissions": sorted(principal.permissions),
        "modules": ["psm"],
        "navigation": [],
        "csrf_token": csrf.token_for(token),
    }


class PreviewLogin(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        key = request.data.get("key", "")
        if not isinstance(key, str) or not secrets.compare_digest(key, settings.PSM_PREVIEW_KEY):
            return Response({"error": {"message": "Enter the preview access key."}}, status=403)
        role = request.data.get("role", "ps_admin")
        row = Membership.objects.filter(role=role).order_by("user_id").first()
        if row is None:
            return Response({"error": {"message": "Unknown preview role."}}, status=400)
        token = signing.dumps(row.user_id, salt="psm-preview")
        result = Response(payload(resolve_token(token), token))
        result.set_cookie(
            COOKIE, token, httponly=True, secure=not settings.DEBUG, samesite="Lax", max_age=86400
        )
        return result


class PreviewMe(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        principal = getattr(request, "principal", None)
        return Response(payload(principal, request.auth) if principal else None)
