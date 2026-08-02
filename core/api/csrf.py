"""CSRF for cookie-borne credentials, checked in the authentication classes —
the one layer that knows how the credential arrived.

The token is HMAC(SECRET_KEY, session): stored nowhere, bound to one session.
Backs up SameSite=Lax for a same-site subdomain or a browser that ignores it.
"""
from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

HEADER = "HTTP_X_CSRF_TOKEN"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def token_for(session_value: str) -> str:
    """The token that pairs with this session. Derived, never stored."""
    return hmac.new(settings.SECRET_KEY.encode(),
                    f"csrf:{session_value}".encode(),
                    hashlib.sha256).hexdigest()


def require(request, session_value: str) -> None:
    """Raise unless an unsafe cookie-authenticated request carries it."""
    if request.method in SAFE_METHODS:
        return
    sent = request.META.get(HEADER, "")
    if not hmac.compare_digest(sent, token_for(session_value)):
        raise PermissionDenied(
            "Missing or invalid CSRF token. Send the `csrf_token` from your "
            "session payload in the X-CSRF-Token header.")
