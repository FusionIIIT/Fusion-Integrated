"""Pure Python domain logic, invariants, and state machines for Hostel Management.

NO Django, DRF, or Celery imports allowed in this package.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


# --- Invariants & Validations ---

def validate_room_capacity(capacity: int) -> None:
    """BR-HM-010: Room capacity positivity."""
    if capacity <= 0:
        raise ValueError("Room capacity must be greater than zero")


def check_capacity_guard(capacity: int, current_active_assignments: int) -> None:
    """BR-HM-010: Cannot exceed room capacity."""
    if current_active_assignments >= capacity:
        raise ValueError("Room capacity exceeded")


def validate_stay_dates(start_date: date, end_date: date) -> None:
    """Dates must be valid and non-inverted."""
    if end_date < start_date:
        raise ValueError("End date cannot be earlier than start date")


# --- Declarative State Machines (Section (c)) ---

# 1. Accommodation Request: Submitted -> Allotted / Cancelled
ACCOMMODATION_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("submitted", "allot", "admin"): "allotted",
    ("submitted", "cancel", "student"): "cancelled",
}

# 2. Leave Request: BW-HM-02 / BW-HM-03 / CW-HM-01
# Submitted -> Caretaker approve -> Approved; Caretaker reject -> Rejected
LEAVE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("submitted", "approve", "caretaker"): "approved",
    ("submitted", "reject", "caretaker"): "rejected",
    ("submitted", "cancel", "student"): "cancelled",
}

# 3. Complaint Handling: BW-HM-04 / BW-HM-05 / CW-HM-02
# Submitted -> Caretaker resolve -> Resolved
# Submitted -> Caretaker update -> Updated (Unresolved)
# Submitted or Updated -> Caretaker escalate -> Escalated
# Updated -> Caretaker resolve -> Resolved
COMPLAINT_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("submitted", "resolve", "caretaker"): "resolved",
    ("submitted", "update", "caretaker"): "updated",
    ("submitted", "escalate", "caretaker"): "escalated",
    ("updated", "resolve", "caretaker"): "resolved",
    ("updated", "update", "caretaker"): "updated",
    ("updated", "escalate", "caretaker"): "escalated",
    ("escalated", "resolve", "warden"): "resolved",
    ("escalated", "update", "warden"): "escalated",
}

# 4. Guest Booking: BW-HM-06 / BW-HM-07 / CW-HM-03
# Submitted -> Caretaker approve -> Approved
# Submitted -> Caretaker reject -> Rejected
GUEST_BOOKING_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("submitted", "approve", "caretaker"): "approved",
    ("submitted", "reject", "caretaker"): "rejected",
    ("submitted", "cancel", "student"): "cancelled",
}

# 5. Extended Stay: BW-HM-08 / BW-HM-09 / CW-HM-04
# Submitted -> Warden approve -> Approved
# Submitted -> Warden reject -> Rejected
EXTENDED_STAY_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("submitted", "approve", "warden"): "approved",
    ("submitted", "reject", "warden"): "rejected",
    ("submitted", "cancel", "student"): "cancelled",
}

# 6. Notice Lifecycle: Draft -> Published -> Withdrawn
NOTICE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("draft", "publish", "authority"): "published",
    ("published", "withdraw", "authority"): "withdrawn",
}


def transition_state(
    table: dict[tuple[str, str, str], str],
    current_state: str,
    event: str,
    actor_kind: str,
) -> str:
    """Transition pure Python state machine or raise ValueError."""
    key = (current_state.lower(), event.lower(), actor_kind.lower())
    if key not in table:
        raise ValueError(
            f"Invalid state transition: current='{current_state}', event='{event}', actor='{actor_kind}'"
        )
    return table[key]
