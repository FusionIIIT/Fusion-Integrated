"""Which actionable tasks are waiting, and for how long (EL-UC-021).

The clock starts at the transition that put the request in its current state,
not at submission: a request that sat with the Unit Head for a week and then
reached the Registrar five minutes ago is a five-minute-old task.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, NotificationOutbox

SUBSTITUTE_RESPONSE = "substitute_response"
UNIT_HEAD_REVIEW = "unit_head_review"
ESTABLISHMENT_ROUTING = "establishment_routing"
FINAL_SANCTION = "final_sanction"

#: BR-EL-032 and BR-EL-033 act on actionable tasks; APPLICANT_ACTION_REQUIRED
#: is deliberately absent because the person who owes the action is the
#: applicant, and no SLA task class covers chasing them.
TASK_CLASS_BY_STATUS = {
    sm.AWAITING_SUBSTITUTE: SUBSTITUTE_RESPONSE,
    sm.EXTENSION_AWAITING_SUBSTITUTE: SUBSTITUTE_RESPONSE,
    sm.AWAITING_UNIT_HEAD: UNIT_HEAD_REVIEW,
    sm.CANCELLATION_AWAITING_UNIT_HEAD: UNIT_HEAD_REVIEW,
    sm.EXTENSION_AWAITING_UNIT_HEAD: UNIT_HEAD_REVIEW,
    sm.AWAITING_ESTABLISHMENT: ESTABLISHMENT_ROUTING,
    sm.CANCELLATION_AWAITING_ESTABLISHMENT: ESTABLISHMENT_ROUTING,
    sm.EXTENSION_AWAITING_ESTABLISHMENT: ESTABLISHMENT_ROUTING,
    sm.AWAITING_FINAL_SANCTION: FINAL_SANCTION,
    sm.CANCELLATION_AWAITING_FINAL: FINAL_SANCTION,
    sm.EXTENSION_AWAITING_FINAL: FINAL_SANCTION,
    sm.AWAITING_DIRECTOR_SELF_SANCTION: FINAL_SANCTION,
}


@dataclass(frozen=True)
class WaitingTask:
    request_id: int
    task_class: str
    status: str
    designation: str
    waiting_since: datetime
    age_hours: float


def task_class_for(status: str) -> str | None:
    return TASK_CLASS_BY_STATUS.get(status)


def waiting(*, now=None) -> list[WaitingTask]:
    """Every actionable task, with the age of its current step."""
    now = now or timezone.now()
    rows = (LeaveRequest.objects
            .filter(status__in=tuple(TASK_CLASS_BY_STATUS))
            .select_related("parent")
            .order_by("id"))
    tasks: list[WaitingTask] = []
    for row in rows:
        since = _step_started_at(row)
        tasks.append(WaitingTask(
            request_id=row.pk,
            task_class=TASK_CLASS_BY_STATUS[row.status],
            status=row.status,
            designation=row.current_step_designation,
            waiting_since=since,
            age_hours=(now - since).total_seconds() / 3600.0,
        ))
    return tasks


def _step_started_at(request: LeaveRequest) -> datetime:
    last = (request.transitions.order_by("-id")
            .values_list("created_at", flat=True).first())
    return last or request.submitted_at or request.created_at


def notified(dedupe_key: str) -> bool:
    return NotificationOutbox.objects.filter(dedupe_key=dedupe_key).exists()


def reminders_logged() -> dict[str, int]:
    """How many threshold notifications have gone out, by topic."""
    counts: dict[str, int] = {}
    for topic in ("sla.reminder", "sla.escalation"):
        counts[topic] = NotificationOutbox.objects.filter(topic=topic).count()
    return counts
