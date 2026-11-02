
"""Fail-closed authorization helpers for Employee Leave Management."""

from core.api.exceptions import PermissionDeniedError


def require_permission(actor, permission_code: str) -> None:
    """Require an authenticated principal with the specified permission."""
    if actor is None:
        raise PermissionDeniedError(
            "Authentication required.",
            code="not_authenticated",
        )

    check = getattr(actor, "has_permission", None)
    if not callable(check) or not check(permission_code):
        raise PermissionDeniedError(
            "You do not have permission to perform this ELM action.",
            code="permission_denied",
        )


def require_employee_access(
    actor,
    *,
    employee_id: int,
    permission_code: str,
) -> None:
    """Require permission and restrict the operation to the actor's own data."""
    require_permission(actor, permission_code)

    if getattr(actor, "user_id", None) != employee_id:
        raise PermissionDeniedError(
            "You may perform this action only on your own leave records.",
            code="permission_denied",
        )


def require_assigned_authority(
    actor,
    *,
    assigned_user_id: int,
    permission_code: str,
) -> None:
    """Require permission and a match with the assigned authority's IAM ID.

    The caller must resolve assigned_user_id from trusted workflow data.
    Never take it directly from an untrusted request parameter.
    """
    require_permission(actor, permission_code)

    if getattr(actor, "user_id", None) != assigned_user_id:
        raise PermissionDeniedError(
            "You are not the assigned authority for this request.",
            code="permission_denied",
        )
