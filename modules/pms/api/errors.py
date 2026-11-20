"""Translate PMS domain errors into the platform error envelope.

`domain/` is deliberately pure Python — the import-linter contract "domain/
must not import Django, DRF or Celery" forbids raising the platform's
`DomainError` there. The translation therefore belongs at the API boundary,
matching the split placement makes in `services/applications.py` with
`resolve_or_raise`.

Without this layer every `PmsDomainError` escapes DRF's handler untouched and
surfaces as HTTP 500 instead of its intended 4xx (BR-PMS-126, CFR-PMS-027).
"""

from __future__ import annotations

from rest_framework import generics
from rest_framework.views import APIView

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    DomainError,
    PermissionDeniedError,
)
from core.api.exceptions import exception_handler as platform_exception_handler
from modules.pms.domain.errors import (
    AppealNotAllowedError,
    BudgetThresholdExceededError,
    ConflictOfInterestError,
    DeadlineExceededError,
    IncompleteInventorsError,
    InsufficientJustificationError,
    InvalidDocumentError,
    InvalidTransitionError,
    NotificationRecipientError,
    NotPermittedError,
    PmsDomainError,
    PreconditionNotMetError,
    UnauthorizedRoleError,
    WithdrawalNotAllowedError,
)

#: Semantic split, mirroring `core/api/exceptions.py`: authorization refusals
#: are 403, state/conflict refusals 409, malformed input 400. Most specific
#: class first — `isinstance` walks this tuple in order.
_ERROR_MAP: tuple[tuple[type[PmsDomainError], type[DomainError]], ...] = (
    (NotPermittedError, PermissionDeniedError),
    (UnauthorizedRoleError, PermissionDeniedError),
    (ConflictOfInterestError, PermissionDeniedError),
    (NotificationRecipientError, ConflictError),
    (InvalidTransitionError, ConflictError),
    (WithdrawalNotAllowedError, ConflictError),
    (AppealNotAllowedError, ConflictError),
    (DeadlineExceededError, ConflictError),
    (BudgetThresholdExceededError, ConflictError),
    (InsufficientJustificationError, BadRequestError),
    (InvalidDocumentError, BadRequestError),
    (IncompleteInventorsError, BadRequestError),
    (PreconditionNotMetError, BadRequestError),
)


def to_platform_error(exc: PmsDomainError) -> DomainError:
    """Map a PMS domain error onto the platform error that carries its status."""
    for pms_type, platform_type in _ERROR_MAP:
        if isinstance(exc, pms_type):
            return platform_type(exc.message, code=exc.code, details=exc.details)
    return DomainError(exc.message, code=exc.code, details=exc.details)


class PmsErrorMappingMixin:
    """Answer a PMS domain refusal with its HTTP meaning instead of a 500."""

    def handle_exception(self, exc):
        if isinstance(exc, PmsDomainError):
            return platform_exception_handler(
                to_platform_error(exc), {"request": self.request, "view": self}
            )
        return super().handle_exception(exc)


class PmsAPIView(PmsErrorMappingMixin, APIView):
    """Base for every PMS endpoint."""


class PmsListCreateView(PmsErrorMappingMixin, generics.ListCreateAPIView):
    """Same contract for generic list/create endpoints."""
