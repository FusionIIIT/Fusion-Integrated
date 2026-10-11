"""Write authority, stated once. Every service write path calls it.

`scope` proves a row is readable, never that the caller may change it; this is
the gate the service itself enforces so a management command or a task cannot
skip it.
"""
from __future__ import annotations

from core.api.exceptions import PermissionDeniedError


def require(actor, *codes: str) -> None:
    """Admit the actor, or raise PermissionDeniedError."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.",
            code="permission_denied")
