"""Reads over leave requests: queues, live intervals and step tasks."""
from __future__ import annotations

from datetime import date

from django.db.models import QuerySet

from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.domain.validation import Interval
from modules.leave.models import LeaveRequest, SubstituteAssignment

#: Statuses that still block another request on the same dates (BR-EL-012).
BLOCKING_STATUSES = tuple(sorted(sm.PENDING | {sm.APPROVED}))

#: Requests still moving through a decision path.
IN_FLIGHT = tuple(sorted(sm.PENDING))


def open_requests() -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(status__in=IN_FLIGHT)


def step_queue(*, step_kind: str, designation: str = "") -> QuerySet[LeaveRequest]:
    """The queue one step of the configured path actually works from."""
    qs = LeaveRequest.objects.filter(status__in=IN_FLIGHT,
                                     current_step_kind=step_kind)
    if designation:
        qs = qs.filter(current_step_designation=designation)
    return qs.order_by("submitted_at", "id")


def designation_queue(designations) -> QuerySet[LeaveRequest]:
    return (LeaveRequest.objects
            .filter(status__in=IN_FLIGHT,
                    current_step_designation__in=set(designations))
            .order_by("submitted_at", "id"))


def for_user(user_id: int) -> QuerySet[LeaveRequest]:
    return LeaveRequest.objects.filter(user_id=user_id).order_by("-id")


def blocking_for(user_id: int, *, exclude_pk: int | None = None) -> list[LeaveRequest]:
    qs = LeaveRequest.objects.filter(user_id=user_id, status__in=BLOCKING_STATUSES)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return list(qs.order_by("start_date"))


def intervals_for(user_id: int, *, exclude_pk: int | None = None) -> tuple[Interval, ...]:
    return tuple(
        Interval(start=r.start_date, end=r.end_date, half=r.half, category=r.category,
                 reference="approved" if r.status == sm.APPROVED else "pending")
        for r in blocking_for(user_id, exclude_pk=exclude_pk)
    )


def approved_leave(user_id: int, *, category: str = "") -> QuerySet[LeaveRequest]:
    qs = LeaveRequest.objects.filter(user_id=user_id, kind="new", status=sm.APPROVED)
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("-start_date")


def ongoing_leave(user_id: int, *, on_date: date) -> LeaveRequest | None:
    """The approved EL/COL/VL whose interval covers this date, if any."""
    return (LeaveRequest.objects
            .filter(user_id=user_id, status=sm.APPROVED, kind="new",
                    category__in=sorted(cat.EXTENDABLE),
                    start_date__lte=on_date, end_date__gte=on_date)
            .order_by("-start_date").first())


def pending_substitute(request_id: int) -> SubstituteAssignment | None:
    return (SubstituteAssignment.objects.filter(request_id=request_id, state="pending")
            .order_by("-id").first())


def has_open_substitute_request(user_id: int) -> bool:
    return SubstituteAssignment.objects.filter(
        substitute_user_id=user_id, state="pending").exists()
