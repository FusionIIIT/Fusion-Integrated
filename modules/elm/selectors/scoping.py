"""Role scope, decided in one place.

Every list view starts from a queryset built here, so an out-of-scope row is a
404 rather than a 403 and authorisation is never re-derived per endpoint.

    EL-BR-021  an employee sees only their own leave
    EL-BR-030  staff read the module; the approving roles act on what they see
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.elm.models import (
    HolidayCalendar,
    LeaveAccount,
    LeaveRequest,
    SubstituteAssignment,
    WorkflowTask,
)

P_VIEW_ALL = "elm.leave_request.view"
P_VIEW_SELF = "elm.leave_request.view_self"
P_REVIEW = "elm.leave_request.review"
P_ESTABLISHMENT = "elm.leave_request.establishment"
P_SANCTION = "elm.leave_request.sanction"
P_SUBSTITUTE = "elm.substitute.respond"
P_RECORD = "elm.record.manage"

STAFF_SCOPE_PERMISSIONS = (
    P_VIEW_ALL, P_REVIEW, P_ESTABLISHMENT, P_SANCTION, P_RECORD,
)

#: Which permission unlocks which pooled task, so a queue can be built without
#: hard-coding the answer at each endpoint.
ROLE_PERMISSIONS = {
    "substitute": P_SUBSTITUTE,
    "unit_head": P_REVIEW,
    "establishment": P_ESTABLISHMENT,
    "sanction": P_SANCTION,
    "director": P_SANCTION,
}


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def is_staff(actor) -> bool:
    return _has(actor, *STAFF_SCOPE_PERMISSIONS)


def roles_of(actor) -> set[str]:
    return {str(r) for r in getattr(actor, "roles", ())}


# -- Requests ------------------------------------------------------------------
def requests_for(actor) -> QuerySet[LeaveRequest]:
    base = LeaveRequest.objects.select_related("original")
    if is_staff(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(Q(user_id=own) | Q(substitute_user_id=own))


def records_for(actor) -> QuerySet[LeaveRequest]:
    """Approved leave, for the records screen (EL-UC-016)."""
    base = LeaveRequest.objects.filter(status="approved")
    if _has(actor, P_RECORD, P_VIEW_ALL):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()


# -- Tasks ---------------------------------------------------------------------
def work_queue_for(actor) -> QuerySet[WorkflowTask]:
    """Pending tasks addressed to this actor: directly, or by role pool."""
    base = (WorkflowTask.objects
            .filter(status="pending")
            .select_related("request"))
    own = _own_id(actor)
    mine = Q(assigned_to_user_id=own) if own is not None else Q(pk__in=[])
    pooled_roles = [role for role, code in ROLE_PERMISSIONS.items()
                    if _has(actor, code)]
    return base.filter(mine | Q(role__in=pooled_roles, assigned_to_user_id__isnull=True))


# -- Substitutions -------------------------------------------------------------
def substitute_assignments_for(actor) -> QuerySet[SubstituteAssignment]:
    base = SubstituteAssignment.objects.select_related("request")
    if is_staff(actor):
        return base
    own = _own_id(actor)
    return base.filter(substitute_user_id=own) if own is not None else base.none()


# -- Accounts ------------------------------------------------------------------
def accounts_for(actor, *, year: int) -> QuerySet[LeaveAccount]:
    base = LeaveAccount.objects.filter(year=year)
    if is_staff(actor):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()


def may_read_account(actor, user_id: int) -> bool:
    return is_staff(actor) or _own_id(actor) == user_id


# -- Calendar ------------------------------------------------------------------
def calendars_for(actor) -> QuerySet[HolidayCalendar]:
    """Published calendars are public; drafts are for the calendar office."""
    base = HolidayCalendar.objects.all()
    if _has(actor, "elm.calendar.manage"):
        return base
    return base.filter(is_published=True)
