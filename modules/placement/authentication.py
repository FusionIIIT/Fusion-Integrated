"""Recruiter authentication — the only credential check this service performs.

Institute users authenticate at the IAM; this service never sees their
password. Recruiters have no ERP identity, so their credential lives here, in
a separate lane: its own header scheme, and a principal carrying a company but
no permissions, since everything a recruiter may do is decided by scoped
querysets.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from core.api import csrf
from modules.placement.models import RecruiterSession

SESSION_TTL_HOURS = 8
TOUCH_EVERY = timedelta(minutes=1)

# httpOnly, and a different name from the institute session so the two can
# never be confused. The portal never holds a bearer token in JS-readable
# storage. Path-scoped to the API, not "/".
COOKIE_NAME = "recruiter_session"
COOKIE_PATH = "/api/v1/placement"


def make_session_key() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class RecruiterPrincipal:
    """An external recruiter: a company, not an institute identity.

    The absence of `user_id` is load-bearing — code that reaches for it to
    scope institute data fails loudly rather than silently.
    """

    account_id: int
    company_id: int
    email: str
    display_name: str
    kind: str = "recruiter"

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    roles: tuple[str, ...] = ("recruiter",)
    permissions: frozenset[str] = field(default_factory=frozenset)

    # A recruiter holds exactly one module and nothing else. Hard-coded rather
    # than granted, so no data change can widen it.
    modules: tuple[str, ...] = ("placement_cell",)

    def has_permission(self, code: str) -> bool:
        """Always false — reach is defined by scoped querysets, never a grant."""
        return False

    def has_any_permission(self, *codes: str) -> bool:
        return False

    def has_module(self, code: str) -> bool:
        return code == "placement_cell"

    def __str__(self) -> str:
        return f"recruiter:{self.email}@{self.company_id}"


class RecruiterAuthentication(BaseAuthentication):
    keyword = "Recruiter"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        from_cookie = False
        if header.startswith(self.keyword + " "):
            raw = header[len(self.keyword) + 1:].strip()
        elif header:
            # Another scheme is in play. Decline rather than fall back to our
            # cookie, so a request cannot authenticate as two principals.
            return None
        else:
            raw = request.COOKIES.get(COOKIE_NAME, "")
            from_cookie = bool(raw)
        if not raw:
            return None

        session = (RecruiterSession.objects
                   .select_related("account", "account__company")
                   .filter(key=hash_token(raw)).first())
        if session is None or session.revoked_at is not None:
            raise AuthenticationFailed("Invalid or expired session.")
        if session.expires_at <= timezone.now():
            raise AuthenticationFailed("Invalid or expired session.")

        # Re-checked per request: deactivation must take effect immediately,
        # not at the end of an eight-hour session.
        account = session.account
        if not account.is_active:
            raise AuthenticationFailed("Invalid or expired session.")
        if not account.company.can_operate:
            raise AuthenticationFailed(
                "Your company's access is not currently authorized.")

        now = timezone.now()
        if session.last_used_at is None or (now - session.last_used_at) > TOUCH_EVERY:
            RecruiterSession.objects.filter(pk=session.pk).update(last_used_at=now)

        if from_cookie:
            csrf.require(request, raw)

        # Downstream code reads request.principal without caring which pool
        # the caller came from.
        principal = RecruiterPrincipal(
            account_id=account.pk, company_id=account.company_id,
            email=account.email, display_name=account.full_name or account.email,
        )
        request.principal = principal
        return (principal, raw)

    def authenticate_header(self, request):
        return self.keyword
