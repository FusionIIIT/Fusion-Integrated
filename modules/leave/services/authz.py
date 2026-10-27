"""Write authority for Leave services."""
from core.api.exceptions import PermissionDeniedError


def require(actor, permission: str) -> None:
    if actor is None or not actor.has_permission(permission):
        raise PermissionDeniedError("You do not have permission to perform this action.")
