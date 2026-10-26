"""The leave request state machine.

Pure Python: declarative status transitions and validation.
No Django or DRF imports.
"""
from __future__ import annotations

import datetime

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"

TERMINAL_STATES = frozenset({APPROVED, REJECTED})

# (current_status, next_status) -> permission required
TRANSITIONS: dict[tuple[str, str], str] = {
    (PENDING, APPROVED): "elm.leave_request.review",
    (PENDING, REJECTED): "elm.leave_request.review",
}


class InvalidTransitionError(Exception):
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            f"Cannot transition leave request from {current_status!r} to {target_status!r}."
        )
        self.current_status = current_status
        self.target_status = target_status


def can_transition(current_status: str, target_status: str) -> bool:
    return (current_status, target_status) in TRANSITIONS


def validate_transition(current_status: str, target_status: str) -> str:
    if (current_status, target_status) not in TRANSITIONS:
        raise InvalidTransitionError(current_status, target_status)
    return TRANSITIONS[(current_status, target_status)]


def calculate_leave_days(start_date: datetime.date, end_date: datetime.date) -> int:
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date.")
    return (end_date - start_date).days + 1
