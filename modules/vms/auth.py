"""Visitor authentication (decision D-1): an opaque cookie token, stored hashed.

Visitors are not IAM principals. `VisitorSessionAuthentication` resolves the
`vms_visitor` cookie to a verified, unexpired `VisitorSession` and sets
`request.visitor`. Lane A adds only the OTP issue/verify services that create
and verify sessions; lane E reuses this class for pass retrieval.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from core.api import csrf
from modules.vms.models import VisitorSession

COOKIE_NAME = "vms_visitor"
COOKIE_PATH = "/api/v1/vms"
SESSION_TTL_HOURS = 12
MAX_OTP_ATTEMPTS = 5


def make_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class VisitorPrincipal:
    """An external visitor. No `user_id` on purpose: code that reaches for it
    to scope institute data fails loudly. Holds no IAM permissions."""
    visitor_id: int
    email: str
    display_name: str
    kind: str = "visitor"
    roles: tuple[str, ...] = ("visitor",)
    permissions: frozenset[str] = frozenset()
    modules: tuple[str, ...] = ()
    is_authenticated: bool = True
    is_anonymous: bool = False

    def has_permission(self, code: str) -> bool:
        return False

    def has_any_permission(self, *codes: str) -> bool:
        return False

    def has_module(self, code: str) -> bool:
        return False


class VisitorSessionAuthentication(BaseAuthentication):
    keyword = "VisitorSession"

    def authenticate(self, request):
        raw = request.COOKIES.get(COOKIE_NAME, "")
        if not raw:
            return None   # anonymous; the permission class decides
        session = (VisitorSession.objects.select_related("visitor")
                   .filter(token_hash=hash_token(raw)).first())
        if (session is None or session.verified_at is None
                or session.expires_at <= timezone.now()):
            raise AuthenticationFailed("Invalid or expired visitor session.")
        csrf.require(request, raw)        # the cookie is ambient
        visitor = session.visitor
        principal = VisitorPrincipal(
            visitor_id=visitor.pk, email=visitor.email, display_name=visitor.full_name)
        request.visitor = visitor
        request.principal = principal
        return (principal, raw)

    def authenticate_header(self, request):
        return self.keyword


class IsVisitorSession(BasePermission):
    message = "A verified visitor session is required."

    def has_permission(self, request, view):
        return isinstance(getattr(request, "principal", None), VisitorPrincipal)
