"""Write authority, stated once."""
from __future__ import annotations

from core.api.exceptions import PermissionDeniedError


def is_recruiter(actor) -> bool:
    return getattr(actor, "kind", None) == "recruiter"


def require(actor, *codes: str, allow_recruiter: bool = False) -> None:
    """Admit the actor, or raise PermissionDeniedError."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")

    if is_recruiter(actor):
        if allow_recruiter:
            return
        raise PermissionDeniedError(
            "This action is not available to a company account.",
            code="permission_denied")

    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.",
            code="permission_denied")
