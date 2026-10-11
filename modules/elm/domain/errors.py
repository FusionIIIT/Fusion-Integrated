"""ELM domain errors.

Plain exceptions, deliberately: ``domain/`` may not import Django, DRF or
Celery (import-linter contract). The API layer translates these into the
platform error envelope; services raise the HTTP-shaped ones from
``core.api.exceptions`` where a status is wanted.
"""
from __future__ import annotations


class ElmError(Exception):
    """Base for every ELM domain failure."""

    code = "elm_error"
    message = "The leave request could not be processed."

    def __init__(self, message: str | None = None, *, code: str | None = None,
                 details: list | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class InvalidTransition(ElmError):
    """The requested move is not in the state-transition table."""

    code = "invalid_transition"

    def __init__(self, frm: str, to: str | None = None):
        super().__init__(
            f"Cannot move a leave request from {frm!r}"
            + (f" to {to!r}" if to else "") + ".")
        self.frm = frm
        self.to = to


class GuardFailed(ElmError):
    """A transition guard (eligibility, calendar, balance, overlap) failed."""

    code = "guard_failed"

    def __init__(self, guard: str, message: str):
        super().__init__(message)
        self.guard = guard


class NotActor(ElmError):
    """The caller may not perform this step on this request."""

    code = "not_actor"


class InsufficientBalance(ElmError):
    code = "insufficient_balance"

    def __init__(self, category: str, available, requested):
        super().__init__(
            f"Available {category} balance ({available}) is less than the "
            f"requested leave ({requested}).")
        self.category = category
        self.available = available
        self.requested = requested


class OverlappingLeave(ElmError):
    code = "overlapping_leave"


class CalendarViolation(ElmError):
    """The requested dates violate the holiday/RH calendar or vacation rules."""

    code = "calendar_violation"


class SubstituteIneligible(ElmError):
    code = "substitute_ineligible"


class ConsentGateClosed(ElmError):
    """Required substitute consent has not been accepted (BR-EL-015)."""

    code = "consent_gate_closed"


class RecordInconsistent(ElmError):
    """Offline-sanctioned entry failed the record-consistency validation."""

    code = "record_inconsistent"
