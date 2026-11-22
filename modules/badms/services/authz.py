from core.api.exceptions import PermissionDeniedError
from modules.badms.domain.departments import department_code


def require(actor, permission: str) -> None:
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not check(permission):
        raise PermissionDeniedError(
            f"This action requires {permission}.", code="permission_denied",
        )


def require_department_role(actor, department: str) -> None:
    role = getattr(actor, "active_role", None) or ""
    if not role.startswith("HOD (") or not role.endswith(")"):
        raise PermissionDeniedError(
            "This request is outside your department.", code="permission_denied",
        )
    if department_code(role[5:-1]) != department_code(department):
        raise PermissionDeniedError(
            "This request is outside your department.", code="permission_denied",
        )
