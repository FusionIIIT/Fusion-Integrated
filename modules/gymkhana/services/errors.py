"""Translate domain refusals into the platform's error types."""
from __future__ import annotations

from rest_framework import status

from core.api.exceptions import ConflictError, DomainError
from modules.gymkhana.domain.rules import RuleViolation


class IdentityUnavailableError(DomainError):
    code = "identity_service_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "The institute directory cannot be reached right now. Try again in a few minutes."


def refused(exc: RuleViolation) -> DomainError:
    """A clash with stored state is a 409; a malformed value is a 422."""
    details = [{"field": exc.field, "message": exc.message}] if exc.field else []
    if exc.conflict:
        return ConflictError(exc.message, code=exc.code, details=details)
    return DomainError(exc.message, code=exc.code, details=details)
