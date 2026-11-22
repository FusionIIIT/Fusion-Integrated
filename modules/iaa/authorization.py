"""Central authorization helpers for service entry points."""

from core.api.exceptions import PermissionDeniedError


class AuthorizationError(PermissionDeniedError):
    """Raised when the active Fusion principal lacks an IAA capability."""


def actor_id(actor) -> int:
    value = getattr(actor, "user_id", None) or getattr(actor, "id", None)
    if value is None:
        raise AuthorizationError("An authenticated institute user is required.")
    return int(value)


def active_role(actor) -> str:
    role = getattr(actor, "active_role", None)
    if not role:
        raise AuthorizationError("Select an active IAA role before acting.")
    raw = str(role).strip().lower()
    compact = " ".join(raw.replace("_", " ").split())
    if compact == "basic user":
        return "basic_user"
    if compact.startswith("hod"):
        return "hod"
    if compact.startswith("dean"):
        return "dean"
    if compact == "director":
        return "director"
    if compact in {"finance staff", "finance"}:
        return "finance_staff"
    if compact in {"auditor", "audit staff"}:
        return "auditor"
    if compact in {"system admin", "system administrator"}:
        return "system_admin"
    return compact.replace(" ", "_")


def require(actor, permission: str, *, roles: set[str] | None = None) -> str:
    if actor is None:
        raise AuthorizationError("Authentication is required.")
    role = active_role(actor)
    if roles is not None and role not in roles:
        raise AuthorizationError("The active role is not eligible for this action.")
    has = getattr(actor, "has_permission", None)
    if has is None or not has(permission):
        raise AuthorizationError("The active role is not permitted to perform this action.")
    return role
