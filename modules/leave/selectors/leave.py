"""Every read this module performs, with ownership filtering in one place.

A view never touches `LeaveRequest.objects`; it starts from a queryset built
here, so a row the caller may not see is a 404 rather than a 403 — the same
reasoning as placement's `selectors/scoping.py`: a 403 confirms existence, and
for leave data the existence of a request is itself the sensitive part.

Scope is decided by the grant that widened it:

    leave.request.view_self   own requests and own balance
    leave.request.approve     the tasks routed to an office the caller holds
    leave.request.view        every request, for records and reporting
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from django.db.models import QuerySet
from django.utils import timezone

from modules.leave.domain import eligibility
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    HierarchyStep,
    HolidayCalendar,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveRequest,
    LeaveResumption,
    LeaveSubstituteAssignment,
    SlaThreshold,
    WorkflowTask,
)

P_VIEW_SELF = "leave.request.view_self"
P_VIEW = "leave.request.view"
P_APPROVE = "leave.request.approve"
P_MANAGE = "leave.type.manage"

#: Statuses that occupy the applicant's calendar (BR-EL-012).
ACTIVE_STATUSES: tuple[str, ...] = (*sorted(sm.PENDING), sm.APPROVED, sm.EXTENDED)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def _user_id(actor) -> int | None:
    """None means there is no identity to scope by, which resolves to nothing.

    Deny is the only safe reading of "who is asking?" being unanswerable.
    """
    return getattr(actor, "user_id", None)


def _roles(actor) -> tuple[str, ...]:
    return tuple(getattr(actor, "roles", ()) or ())


def is_reviewer(actor) -> bool:
    """Sees tasks and the request queue beyond their own leave."""
    return _has(actor, P_APPROVE, P_VIEW, P_MANAGE)


# -- Requests ------------------------------------------------------------------
def requests_for(actor) -> QuerySet[LeaveRequest]:
    base = LeaveRequest.objects.all()
    own = _user_id(actor)
    if own is None:
        return base.none()
    if _has(actor, P_VIEW, P_MANAGE):
        return base
    if _has(actor, P_APPROVE):
        # An approver sees their own leave plus what they have already acted on.
        return (base.filter(user_id=own)
                | base.filter(transitions__actor_user_id=own)).distinct()
    return base.filter(user_id=own)


def request_for(actor, request_id: int) -> LeaveRequest | None:
    return requests_for(actor).filter(pk=request_id).first()


# -- Balances and the ledger ---------------------------------------------------
def balances_of(user_id: int, leave_year: int | None = None) -> QuerySet[LeaveBalance]:
    year = leave_year or timezone.localdate().year
    return (LeaveBalance.objects.filter(user_id=user_id, leave_year=year)
            .order_by("category"))


def balance_of(user_id: int, category: str, leave_year: int) -> LeaveBalance | None:
    return LeaveBalance.objects.filter(user_id=user_id, category=category,
                                       leave_year=leave_year).first()


def ledger_for(user_id: int, leave_year: int | None = None) -> QuerySet[LeaveLedgerEntry]:
    qs = LeaveLedgerEntry.objects.filter(user_id=user_id)
    if leave_year is not None:
        qs = qs.filter(leave_year=leave_year)
    return qs


def active_intervals(*, user_id: int, exclude_request_ids: Sequence[int] = ()
                     ) -> list[eligibility.Interval]:
    """The employee's own pending or approved leave, for the overlap rule."""
    rows = (LeaveRequest.objects
            .filter(user_id=user_id, status__in=ACTIVE_STATUSES)
            .exclude(pk__in=[int(i) for i in exclude_request_ids])
            .values_list("period_from", "period_to", "category", "half"))
    return [eligibility.Interval(start, end, category, half)
            for start, end, category, half in rows]


# -- Configuration -------------------------------------------------------------
def current_policy(leave_year: int | None = None) -> LeavePolicy | None:
    """BR-EL-030 — the current configured parameters, not a published version."""
    year = leave_year or timezone.localdate().year
    return (LeavePolicy.objects.filter(leave_year=year, is_current=True).first()
            or LeavePolicy.objects.filter(is_current=True)
            .order_by("-leave_year").first())


def effective_calendar(leave_year: int | None = None) -> HolidayCalendar | None:
    """BR-EL-031 — the currently effective *published* holiday/RH calendar."""
    year = leave_year or timezone.localdate().year
    return (HolidayCalendar.objects
            .filter(leave_year=year, is_effective=True, published_at__isnull=False)
            .order_by("-published_at").first())


def closed_holidays(leave_year: int | None = None) -> set[date]:
    calendar = effective_calendar(leave_year)
    if calendar is None:
        return set()
    return set(calendar.entries.filter(kind="closed_holiday")
               .values_list("date", flat=True))


def rh_dates(leave_year: int | None = None) -> set[date]:
    calendar = effective_calendar(leave_year)
    if calendar is None:
        return set()
    return set(calendar.entries.filter(kind="restricted_holiday")
               .values_list("date", flat=True))


def hierarchy_rules() -> list[dict]:
    """The current hierarchy configuration, as plain mappings (BR-EL-019)."""
    return list(HierarchyStep.objects.filter(is_active=True).values(
        "category", "unit", "designation", "step_order", "step_kind",
        "authority", "label", "is_active"))


def sla_thresholds() -> dict[str, SlaThreshold]:
    return {t.task_class: t for t in SlaThreshold.objects.filter(is_active=True)}


# -- Tasks: the approver's queue and the substitute's assignment ---------------
def _visible_tasks(actor) -> QuerySet[WorkflowTask]:
    base = WorkflowTask.objects.select_related("request")
    own = _user_id(actor)
    clauses = None
    if own is not None:
        clauses = base.filter(assignee_user_id=own)
    roles = _roles(actor)
    if roles:
        by_role = base.filter(assignee_user_id__isnull=True, assignee_role__in=roles)
        clauses = by_role if clauses is None else (clauses | by_role)
    if clauses is None:
        return base.none()
    return clauses.distinct()


def tasks_for(actor, *, status: str | None = None) -> QuerySet[WorkflowTask]:
    """Tasks the caller can act on: assigned to them, or routed to their office."""
    if not is_reviewer(actor) and not _roles(actor):
        return WorkflowTask.objects.none()
    qs = _visible_tasks(actor)
    if status:
        qs = qs.filter(status=status)
    return qs


def active_tasks_for(actor) -> QuerySet[WorkflowTask]:
    return tasks_for(actor, status="pending")


def task_for(actor, task_id: int) -> WorkflowTask | None:
    return _visible_tasks(actor).filter(pk=task_id).first()


def substitute_assignments_for(actor) -> QuerySet[LeaveSubstituteAssignment]:
    """Responsibility requests nominated to the caller (EL-UC-002).

    No permission gate: the assignment *is* the authority (BR-EL-014), and a
    substitute is any employee, not an approver.
    """
    own = _user_id(actor)
    if own is None:
        return LeaveSubstituteAssignment.objects.none()
    return (LeaveSubstituteAssignment.objects
            .filter(nominee_user_id=own)
            .exclude(status="superseded"))


def assignable_employee(*, nominee_user_id: int, applicant_user_id: int,
                        exists: bool) -> bool:
    """BR-EL-014 — the nominee must be another existing employee."""
    return bool(exists) and nominee_user_id != applicant_user_id


# -- Resumption (EL-UC-010/011) ------------------------------------------------
def resumptions_for(actor) -> QuerySet[LeaveResumption]:
    base = LeaveResumption.objects.select_related("request")
    own = _user_id(actor)
    if own is None:
        return base.none()
    if is_reviewer(actor):
        return base
    return base.filter(user_id=own)


def resumption_for(actor, resumption_id: int) -> LeaveResumption | None:
    return resumptions_for(actor).filter(pk=resumption_id).first()


def pending_resumption_for_request(request_id: int) -> LeaveResumption | None:
    return (LeaveResumption.objects.filter(request_id=request_id, outcome="pending")
            .order_by("-id").first())
