"""Write authority, stated once. Every service write path calls it.

Reads are scoped by `selectors.scoping` (a row you may not see is a 404);
this module is the 403: you can see it, but you may not do that to it.
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


def require_employee(actor) -> None:
    """Only faculty and staff may apply or respond as a substitute; students
    hold no leave identity at all (PS §5, BR-EL-001)."""
    require(actor, "leave.request.view_self")
    if getattr(actor, "kind", None) not in ("faculty", "staff"):
        raise PermissionDeniedError("Leave is available to employees only.",
                                    code="permission_denied")


def require_applicant(actor, request) -> None:
    if getattr(actor, "user_id", None) != request.user_id:
        raise PermissionDeniedError(
            "Only the applicant may act on their own request.",
            code="permission_denied")


def require_user(actor, user_id: int) -> None:
    """Identity gate for a step assigned to a specific desk."""
    if getattr(actor, "user_id", None) != user_id:
        raise PermissionDeniedError(
            "This request is assigned to someone else.",
            code="permission_denied")
