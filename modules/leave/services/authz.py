"""Write authority, stated once: every service write path calls it (BR-EL-036)."""
from __future__ import annotations

from core.api.exceptions import PermissionDeniedError
from modules.leave.domain import categories as cat


def require(actor, *codes: str) -> None:
    if actor is None or getattr(actor, "user_id", None) is None:
        raise PermissionDeniedError("Sign in to use Leave.", code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(f"This action needs {' or '.join(codes)}.",
                                    code="permission_denied")


def require_employee(actor) -> None:
    """Leave is for faculty and staff; a student or operator holds no leave account."""
    if getattr(actor, "kind", None) not in cat.EMPLOYEE_KINDS:
        raise PermissionDeniedError("Only faculty and staff can apply for leave.",
                                    code="not_an_employee")


def acting_role(actor) -> str:
    return (getattr(actor, "active_role", None) or "").strip()
