"""Domain exceptions -> platform DomainErrors, so a service stays callable
from a task or a command and the API layer maps them to HTTP in one place."""
from __future__ import annotations

from contextlib import contextmanager

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.dept.domain.state_machine import ActorNotAllowed, InvalidTransition
from modules.dept.domain.visibility import IncompleteAnnouncement


@contextmanager
def translated():
    try:
        yield
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    except ActorNotAllowed as exc:
        raise PermissionDeniedError(str(exc), code="permission_denied") from exc
    except IncompleteAnnouncement as exc:
        raise ConflictError(str(exc), code="announcement_incomplete") from exc


def require(principal, permission: str) -> None:
    if not principal.has_permission(permission):
        raise PermissionDeniedError(f"This action needs {permission}.",
                                    code="permission_denied")
