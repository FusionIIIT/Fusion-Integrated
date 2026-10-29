"""State machine and business invariants for Employee Leave Management.

Pure Python with zero Django/DRF dependencies.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import StrEnum

from modules.elm.domain.errors import InvalidDateRangeError, InvalidTransitionError


class LeaveCategory(StrEnum):
    CASUAL = "casual"
    MEDICAL = "medical"
    SPECIAL_CASUAL = "special_casual"
    EARNED = "earned"
    COMPENSATORY = "compensatory"
    VACATION = "vacation"


class LeaveStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = frozenset({
    LeaveStatus.APPROVED,
    LeaveStatus.REJECTED,
    LeaveStatus.CANCELLED,
})


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    required_permission: str | None = None
    description: str = ""


TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        frm=LeaveStatus.PENDING,
        to=LeaveStatus.APPROVED,
        required_permission="elm.leave_application.manage",
        description="HR approves a pending leave request",
    ),
    Transition(
        frm=LeaveStatus.PENDING,
        to=LeaveStatus.REJECTED,
        required_permission="elm.leave_application.manage",
        description="HR rejects a pending leave request",
    ),
    Transition(
        frm=LeaveStatus.PENDING,
        to=LeaveStatus.CANCELLED,
        required_permission="elm.leave_application.apply",
        description="Employee cancels their own pending leave request",
    ),
)


def validate_transition(frm: str, to: str) -> None:
    """Validate that moving from `frm` to `to` is legally permitted."""
    if frm in TERMINAL_STATUSES:
        raise InvalidTransitionError(frm, to)

    for t in TRANSITIONS:
        if t.frm == frm and t.to == to:
            return

    raise InvalidTransitionError(frm, to)


def validate_dates(start_date: datetime.date, end_date: datetime.date) -> None:
    """Validate leave date range."""
    if end_date < start_date:
        raise InvalidDateRangeError("Leave end date cannot be earlier than start date.")
