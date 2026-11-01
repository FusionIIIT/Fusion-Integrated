"""Write authority, stated once. Every service write path calls it.

`scope` proves a row is readable, which every student's own application is —
never that the caller may change it. Recruiters hold no permission codes by
construction, so they are admitted by lane rather than by grant.
"""
from __future__ import annotations

from core.api.exceptions import PermissionDeniedError


def require(actor, *codes: str) -> None:
    """Admit the actor, or raise PermissionDeniedError.

    Checks if the actor is authenticated and has at least one of the required codes.
    """
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")

    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.",
            code="permission_denied")
