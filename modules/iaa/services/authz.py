"""Active-role resolution and fail-closed IAA permission checks."""
from modules.iaa.domain.state_machine import (
    ADMIN, AUDITOR, BASIC_USER, DEAN, DIRECTOR, FINANCE, HOD,
)
from modules.iaa.models import IaaRoleAssignment
from modules.iaa.registry import ROLE_GRANTS

IAA_ROLES = frozenset({BASIC_USER, FINANCE, HOD, DEAN, DIRECTOR, AUDITOR, ADMIN})


class IaaAccessError(PermissionError):
    pass


def available_roles(principal) -> tuple[str, ...]:
    if principal is None:
        return ()
    assigned = set(IaaRoleAssignment.objects.filter(
        user_id=principal.user_id, is_active=True
    ).values_list("role", flat=True))
    # IAM role claims are trusted role assignments. Locally assigned roles are
    # IAA-specific additions controlled by the System Admin use case.
    assigned.update(role for role in principal.roles if role in IAA_ROLES)
    return tuple(sorted(assigned))


def active_role(request, *, required=False) -> str | None:
    principal = getattr(request, "principal", None)
    if principal is None:
        return None
    selected = request.headers.get("X-IAA-Active-Role")
    if not selected:
        selected = getattr(request, "query_params", {}).get("active_role")
    if not selected:
        selected = getattr(request, "data", {}).get("active_role")
    roles = available_roles(principal)
    if not selected and len(roles) == 1:
        selected = roles[0]
    if selected not in roles:
        return None
    return selected


def role_has_permission(principal, role: str, code: str) -> bool:
    if role not in available_roles(principal):
        return False
    return code in ROLE_GRANTS.get(role, ())


def require(principal, role: str, code: str) -> None:
    if not principal or role not in available_roles(principal):
        raise IaaAccessError("An assigned active IAA role is required.")
    if code not in ROLE_GRANTS.get(role, ()):
        raise IaaAccessError("This active IAA role cannot perform that action.")


def require_admin(principal, role: str) -> None:
    require(principal, role, "iaa.configuration.manage")
