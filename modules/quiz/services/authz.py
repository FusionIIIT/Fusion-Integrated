"""Small permission boundary helpers for trusted platform principals."""

from core.api.exceptions import PermissionDeniedError


def require_permission(actor: object, permission_code: str) -> None:
    """Require a principal permission without mapping IAM designations locally."""

    check = getattr(actor, "has_permission", None)
    if not callable(check) or not check(permission_code):
        raise PermissionDeniedError(
            f"This Quiz operation requires {permission_code}.", code="permission_denied"
        )
