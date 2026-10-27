"""Pure validation helpers for ELM leave requests."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from modules.elm.domain.leave_days import calculate_chargeable_days

LEAVE_CATEGORIES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})
HALF_DAYS = frozenset({"FIRST", "SECOND"})


class LeaveRequestState(StrEnum):
    """New-request workflow states that have defined overlap semantics."""

    DRAFT = "DRAFT"
    PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE"
    APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED"
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD"
    PENDING_ESTABLISHMENT = "PENDING_ESTABLISHMENT"
    PENDING_FINAL_DECISION = "PENDING_FINAL_DECISION"
    PENDING_DIRECTOR_SANCTION = "PENDING_DIRECTOR_SANCTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    WITHDRAWN = "WITHDRAWN"


_BLOCKING_STATES = frozenset(
    {
        LeaveRequestState.PENDING_SUBSTITUTE,
        LeaveRequestState.APPLICANT_ACTION_REQUIRED,
        LeaveRequestState.PENDING_UNIT_HEAD,
        LeaveRequestState.PENDING_ESTABLISHMENT,
        LeaveRequestState.PENDING_FINAL_DECISION,
        LeaveRequestState.PENDING_DIRECTOR_SANCTION,
        LeaveRequestState.APPROVED,
    }
)
_NONBLOCKING_STATES = frozenset(
    {
        LeaveRequestState.DRAFT,
        LeaveRequestState.REJECTED,
        LeaveRequestState.CANCELLED,
        LeaveRequestState.WITHDRAWN,
    }
)


class LeaveRequestValidationError(ValueError):
    """A caller-readable request validation error."""

    def __init__(self, field: str, code: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExistingLeaveRequest:
    """The overlap-relevant projection of an existing request."""

    start_date: date
    end_date: date
    leave_type: str
    status: LeaveRequestState | str
    half_day: str | None = None


def _validate_request_shape(
    *, leave_type: str, start_date: date, end_date: date, half_day: str | None
) -> None:
    if not isinstance(start_date, date) or isinstance(start_date, datetime):
        raise LeaveRequestValidationError(
            "start_date", "invalid_date", "Start date must be a date value."
        )
    if not isinstance(end_date, date) or isinstance(end_date, datetime):
        raise LeaveRequestValidationError(
            "end_date", "invalid_date", "End date must be a date value."
        )
    if start_date > end_date:
        raise LeaveRequestValidationError(
            "date_range", "reversed_range", "Start date must not be after end date."
        )
    if not isinstance(leave_type, str) or leave_type not in LEAVE_CATEGORIES:
        raise LeaveRequestValidationError(
            "leave_type", "unsupported_category", "Leave category is not supported."
        )
    if half_day is not None and (not isinstance(half_day, str) or half_day not in HALF_DAYS):
        raise LeaveRequestValidationError(
            "half_day", "invalid_half_day", "Half day must be FIRST or SECOND."
        )
    if half_day is not None and leave_type != "CL":
        raise LeaveRequestValidationError(
            "half_day", "unsupported_half_day", "Half-day requests are supported only for CL."
        )
    if half_day is not None and start_date != end_date:
        raise LeaveRequestValidationError(
            "half_day", "invalid_half_day_range", "A CL half-day must cover one date."
        )


def validate_leave_request(
    *,
    leave_type: str,
    start_date: date,
    end_date: date,
    purpose: str,
    half_day: str | None = None,
) -> Decimal:
    """Validate required request fields and return the defined charge quantity.

    Unsupported category/form counting errors from the day calculator are
    deliberately allowed to propagate unchanged.
    """
    if not isinstance(purpose, str) or not purpose.strip():
        raise LeaveRequestValidationError("purpose", "required", "Purpose or reason is required.")

    _validate_request_shape(
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
    )
    return calculate_chargeable_days(start_date, end_date, leave_type, half_day=half_day)


def _state(value: LeaveRequestState | str) -> LeaveRequestState:
    try:
        return LeaveRequestState(value)
    except (TypeError, ValueError) as exc:
        raise LeaveRequestValidationError(
            "status", "unknown_state", f"Unknown leave-request state: {value!r}."
        ) from exc


def ensure_no_overlap(
    *,
    leave_type: str,
    start_date: date,
    end_date: date,
    half_day: str | None,
    existing_requests: Iterable[ExistingLeaveRequest],
) -> None:
    """Reject overlaps with active pending or approved requests.

    Different same-date CL halves are the only overlapping calendar intervals
    that are explicitly permitted by BR-EL-012.
    """
    _validate_request_shape(
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
    )

    for request in existing_requests:
        state = _state(request.status)
        if state in _NONBLOCKING_STATES:
            continue
        if state not in _BLOCKING_STATES:
            # Defensive if the state sets and enum ever diverge.
            raise LeaveRequestValidationError(
                "status", "unknown_state", f"Unknown leave-request state: {state!r}."
            )

        _validate_request_shape(
            leave_type=request.leave_type,
            start_date=request.start_date,
            end_date=request.end_date,
            half_day=request.half_day,
        )
        if start_date > request.end_date or request.start_date > end_date:
            continue

        different_cl_halves = (
            leave_type == "CL"
            and request.leave_type == "CL"
            and start_date == end_date == request.start_date == request.end_date
            and half_day is not None
            and request.half_day is not None
            and half_day != request.half_day
        )
        if different_cl_halves:
            continue

        raise LeaveRequestValidationError(
            "date_range", "overlap", "Request overlaps an active pending or approved leave."
        )


def validate_available_balance(available: Decimal, chargeable: Decimal) -> None:
    """Check a supplied balance without reading or mutating any account."""
    if not isinstance(available, Decimal) or not isinstance(chargeable, Decimal):
        raise LeaveRequestValidationError(
            "balance", "decimal_required", "Available and chargeable quantities must be Decimal."
        )
    if not available.is_finite() or not chargeable.is_finite():
        raise LeaveRequestValidationError(
            "balance", "invalid_decimal", "Available and chargeable quantities must be finite."
        )
    if available < 0:
        raise LeaveRequestValidationError(
            "available_balance", "negative_balance", "Available balance cannot be negative."
        )
    if chargeable < 0:
        raise LeaveRequestValidationError(
            "chargeable_days", "negative_quantity", "Chargeable quantity cannot be negative."
        )
    if available < chargeable:
        raise LeaveRequestValidationError(
            "available_balance", "insufficient_balance", "Available balance is insufficient."
        )
