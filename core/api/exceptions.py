"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)
