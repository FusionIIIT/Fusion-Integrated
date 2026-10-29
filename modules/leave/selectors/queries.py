"""Read-side querysets for the leave module.

All of them begin from `scoping`, so there is exactly one place where visibility
is decided and no endpoint can accidentally build an unscoped queryset.
"""
from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    ApprovalTask,
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveRequest,
)
from modules.leave.models.requests import TASK_PENDING
from modules.leave.selectors import scoping

#: Statuses in which the request is still moving and still consumes nothing.
OPEN_STATES: tuple[str, ...] = sm.PENDING
#: Statuses that have consumed days and are not yet returned.
ACTIVE_STATES: tuple[str, ...] = (sm.APPROVED,)
#: Statuses that ended the request without any further action.
CLOSED_STATES: tuple[str, ...] = (sm.REJECTED, sm.WITHDRAWN)

#: BR-EL-034: a rejected request is never revived, so these stay closed.
LIFECYCLE_PENDING: tuple[str, ...] = (
    *sm.CANCELLATION_PENDING, *sm.EXTENSION_PENDING, sm.RESUMPTION_PENDING)


def leave_requests(actor, *, status: str = "", category: str = "",
                   year: int | None = None, category_state: str = "") -> QuerySet[LeaveRequest]:
    qs = scoping.requests_for(actor)
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)
    if year is not None:
        qs = qs.filter(start_date__year=year)
    if category_state == "pending":
        qs = qs.filter(status__in=OPEN_STATES)
    elif category_state == "active":
        qs = qs.filter(status__in=ACTIVE_STATES)
    elif category_state == "closed":
        qs = qs.filter(status__in=CLOSED_STATES)
    return qs.order_by("-id")


def request_counts(actor, *, year: int | None = None) -> dict[str, int]:
    """EL-UC-002: the per-status counts on the My Requests screen."""
    qs = leave_requests(actor, year=year)
    rows = qs.values("status").annotate(total=Count("id"))
    counts = {state: 0 for state in sm.LEAVE_STATES}
    counts.update({row["status"]: row["total"] for row in rows})
    return counts


def my_requests(actor) -> QuerySet[LeaveRequest]:
    """EL-UC-001: strictly the caller's own applications."""
    own = getattr(actor, "user_id", None)
    qs = LeaveRequest.objects.all()
    return (qs.none() if own is None
            else qs.filter(user_id=own).select_related("org_unit").order_by("-id"))


def draft_requests(actor) -> QuerySet[LeaveRequest]:
    own = getattr(actor, "user_id", None)
    qs = LeaveRequest.objects.filter(status=sm.DRAFT)
    return (qs.none() if own is None else qs.filter(user_id=own).order_by("-id"))


def overdue_out_of_office(actor, *, today) -> QuerySet[LeaveRequest]:
    """BR-EL-032: approved leave already past its end date and not yet returned."""
    return (scoping.requests_for(actor)
            .filter(status__in=ACTIVE_STATES, end_date__lt=today)
            .exclude(resumptions__status=sm.RESUMPTION_COMPLETED)
            .order_by("end_date"))


def open_task_counts(actor) -> dict[str, int]:
    qs = scoping.tasks_for(actor)
    return {row["kind"]: row["total"] for row in
            qs.values("kind").annotate(total=Count("id"))}


def balances(actor, *, year: int | None = None) -> QuerySet[LeaveBalance]:
    qs = scoping.balances_for(actor)
    return qs.filter(year=year).order_by("category") if year else qs


def balance_map(actor, *, year: int) -> dict[tuple[int, str], LeaveBalance]:
    return {(row.user_id, row.category): row
            for row in balances(actor, year=year).only("user_id", "category", "days")}


def ledger_entries(actor, *, user_id: int | None = None, year: int | None = None,
                   category: str = "") -> QuerySet[LeaveLedgerEntry]:
    """BR-EL-026: an administrator may inspect any account; anyone else is
    narrowed to their own, so this is called with the scoping queryset, not
    the raw table."""
    qs = LeaveLedgerEntry.objects.all()
    own = getattr(actor, "user_id", None)
    if user_id is not None and user_id != own and not scoping._is_leave_administrator(actor):
        return qs.none()
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    elif own is not None and not scoping._is_leave_administrator(actor):
        qs = qs.filter(user_id=own)
    if year is not None:
        qs = qs.filter(year=year)
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("-id")


def escalated_task_count(*, today) -> int:
    return ApprovalTask.objects.filter(
        status=TASK_PENDING, escalation_due_at__lt=today).count()


def reminders_due(*, now) -> QuerySet[ApprovalTask]:
    return ApprovalTask.objects.filter(
        Q(reminder_sent_at__isnull=True), reminder_due_at__isnull=False,
        reminder_due_at__lte=now, status=TASK_PENDING).order_by("reminder_due_at")


def escalations_due(*, now) -> QuerySet[ApprovalTask]:
    return ApprovalTask.objects.filter(
        escalation_due_at__isnull=False, escalation_due_at__lte=now,
        status=TASK_PENDING).order_by("escalation_due_at")