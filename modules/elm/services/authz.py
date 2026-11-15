"""Write authority, stated once."""
from __future__ import annotations

from rest_framework import status

from core.api.exceptions import DomainError, PermissionDeniedError


class DirectoryUnavailable(DomainError):
    code = "directory_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "The identity service is not reachable right now. Please try again shortly."


def require(actor, *codes: str) -> None:
    if actor is None:
        raise PermissionDeniedError("Authentication required.", code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(f"This action needs {' or '.join(codes)}.",
                                    code="permission_denied")
