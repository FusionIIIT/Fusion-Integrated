"""Pure-Python workflow state machine for Graduate Seminar Scheduling (BW-OAP-09).

Participating Use Cases:
- OA-UC-51: Request Graduate Seminar (PG Student)
- OA-UC-53: Schedule Graduate Seminar (Department Administrator)

Business Rules:
- OA-BR-61: PG Scope Check
- OA-BR-62: Department Administrator schedules pending request, records seminar,
  and updates scheduling history.
"""
from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class SeminarStatus(str, Enum):
    NO_SUBMITTED_REQUEST = "NO_SUBMITTED_REQUEST"
    AWAITING_SCHEDULING = "AWAITING_SCHEDULING"
    SCHEDULED = "SCHEDULED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class SeminarEvent(str, Enum):
    SUBMIT = "SUBMIT"
    SCHEDULE = "SCHEDULE"
    REJECT = "REJECT"
    CANCEL = "CANCEL"


class TransitionRule(NamedTuple):
    from_status: SeminarStatus
    event: SeminarEvent
    to_status: SeminarStatus
    actor_role: str
    permission: str
    description: str


#: Declarative state transition table for BW-OAP-09
TRANSITIONS: list[TransitionRule] = [
    # OA-UC-51: Student submits request
    TransitionRule(
        from_status=SeminarStatus.NO_SUBMITTED_REQUEST,
        event=SeminarEvent.SUBMIT,
        to_status=SeminarStatus.AWAITING_SCHEDULING,
        actor_role="student",
        permission="department.seminar.request",
        description="PG Student submits seminar request, entering Awaiting Scheduling."
    ),
    # OA-UC-53: Department Administrator schedules seminar
    TransitionRule(
        from_status=SeminarStatus.AWAITING_SCHEDULING,
        event=SeminarEvent.SCHEDULE,
        to_status=SeminarStatus.SCHEDULED,
        actor_role="department_admin",
        permission="department.seminar.schedule",
        description="Department Administrator schedules the seminar, producing Scheduled state."
    ),
    # Alternate flow: Administrator rejects request
    TransitionRule(
        from_status=SeminarStatus.AWAITING_SCHEDULING,
        event=SeminarEvent.REJECT,
        to_status=SeminarStatus.REJECTED,
        actor_role="department_admin",
        permission="department.seminar.schedule",
        description="Department Administrator rejects the seminar request."
    ),
    # Alternate flow: Student withdraws/cancels request before scheduling
    TransitionRule(
        from_status=SeminarStatus.AWAITING_SCHEDULING,
        event=SeminarEvent.CANCEL,
        to_status=SeminarStatus.CANCELLED,
        actor_role="student",
        permission="department.seminar.request",
        description="Student cancels the pending seminar scheduling request."
    ),
]


def can_transition(
    current_status: str,
    event: str,
) -> tuple[bool, str, TransitionRule | None]:
    """Check if the transition from current_status via event is legal under BW-OAP-09."""
    for rule in TRANSITIONS:
        if rule.from_status.value == current_status and rule.event.value == event:
            return True, f"Transition allowed to {rule.to_status.value}.", rule
    return False, f"Illegal transition from '{current_status}' via event '{event}'.", None


def get_next_status(current_status: str, event: str) -> str:
    """Return next status or raise ValueError."""
    allowed, msg, rule = can_transition(current_status, event)
    if not allowed or rule is None:
        raise ValueError(msg)
    return rule.to_status.value
