from django.conf import settings
from django.core import signing
from rest_framework.authentication import BaseAuthentication

from core.api import csrf
from fusion_auth.principal import Principal
from modules.psm.models import Membership
from modules.psm.registry import PERMISSIONS

COOKIE = "psm_preview_session"


def resolve_token(token):
    if not getattr(settings, "PSM_PREVIEW", False):
        return None
    try:
        uid = signing.loads(token, salt="psm-preview", max_age=86400)
    except signing.BadSignature:
        return None
    row = Membership.objects.filter(user_id=uid).first()
    if row is None:
        return None
    return Principal(
        user_id=uid,
        username=f"demo-{row.role}",
        display_name=row.role.replace("_", " ").title(),
        kind="staff",
        active_role="psm_" + row.role,
        roles=("psm_" + row.role,),
        permissions=frozenset(code for code, _ in PERMISSIONS),
        modules=("psm",),
    )


class PreviewAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get(COOKIE)
        principal = resolve_token(token) if token else None
        if principal is None:
            return None
        csrf.require(request, token)
        request.principal = principal
        return principal, token

    def authenticate_header(self, request):
        return "Preview"
