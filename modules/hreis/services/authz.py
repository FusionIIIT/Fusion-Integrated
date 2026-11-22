"""Two IAM gates plus exact active-role restrictions for HR-EIS writes."""

from core.api.exceptions import PermissionDeniedError

MODULE = "hreis"


def require(actor, permission: str, *, allowed_roles: frozenset[str] | None = None) -> None:
    if actor is None or not (
        callable(getattr(actor, "has_module", None))
        and callable(getattr(actor, "has_permission", None))
        and actor.has_module(MODULE)
        and actor.has_permission(permission)
        and (allowed_roles is None or getattr(actor, "active_role", None) in allowed_roles)
        and getattr(actor, "user_id", None) is not None
    ):
        raise PermissionDeniedError(
            "Select an authorized HR role or ask HR to review your access.",
            code="hreis_role_denied",
        )
