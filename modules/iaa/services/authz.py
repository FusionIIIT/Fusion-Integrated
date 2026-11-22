"""Write authority, stated once; every write path calls `require` first."""
from __future__ import annotations

from core.api.exceptions import PermissionDeniedError


def require(actor, *codes: str) -> None:
    if actor is None:
        raise PermissionDeniedError("Sign in to continue.", code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            "Your active role cannot do this. Switch to the role that can, or ask the IAA "
            "System Admin.", code="permission_denied")


def role_of(actor) -> str:
    return getattr(actor, "active_role", None) or getattr(actor, "kind", "") or ""
