"""Authorization helper: refuse the wrong actor, fail closed."""

from core.api.exceptions import PermissionDeniedError


def require(actor, permission: str) -> None:
    """Raise unless the acting role holds `permission`."""
    if actor is None or not getattr(actor, "has_permission", lambda *_: False)(permission):
        raise PermissionDeniedError(f"This role does not hold {permission}.")
