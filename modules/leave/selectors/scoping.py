"""Whose rows this person sees. Out of scope is 404, never 403."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.directory import contracts as directory
from modules.leave.models import LeaveApplication, LeaveLedgerEntry, WorkflowTask

P_VIEW = "leave.application.view"
P_REVIEW = "leave.application.review"
P_APPROVE = "leave.application.approve"
P_ADMIN = "leave.offline.create"
P_POLICY = "leave.policy.publish"


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def _role(actor) -> str:
    return (getattr(actor, "active_role", None) or "").strip()


def _department(actor) -> str:
    uid = _own_id(actor)
    if uid is None:
        return ""
    users = directory.get_users([uid])
    person = users.get(uid)
    return (person.department if person else "") or ""


def applications_for(actor) -> QuerySet[LeaveApplication]:
    uid = _own_id(actor)
    if uid is None:
        return LeaveApplication.objects.none()
    if _has(actor, P_ADMIN, P_POLICY):
        return LeaveApplication.objects.all()
    qs = LeaveApplication.objects.filter(
        Q(user_id=uid) | Q(substitute_user_id=uid)
    )
    if _has(actor, P_APPROVE, P_REVIEW):
        dept = _department(actor)
        extra = Q()
        if dept:
            extra |= Q(unit_code=dept)
        extra |= Q(applicant_is_director=True)
        extra |= Q(status__in=(
            "awaiting_establishment", "awaiting_final_sanction",
            "awaiting_director_self_sanction", "cancellation_pending",
            "awaiting_resumption_verification",
        ))
        qs = LeaveApplication.objects.filter(
            Q(user_id=uid) | Q(substitute_user_id=uid) | extra
        )
    return qs


def ledger_for(actor, user_id: int | None = None) -> QuerySet[LeaveLedgerEntry]:
    uid = _own_id(actor)
    if uid is None:
        return LeaveLedgerEntry.objects.none()
    target = user_id if user_id is not None else uid
    if target != uid and not _has(actor, P_ADMIN, P_REVIEW, P_APPROVE):
        return LeaveLedgerEntry.objects.none()
    return LeaveLedgerEntry.objects.filter(user_id=target)


def tasks_for(actor) -> QuerySet[WorkflowTask]:
    uid = _own_id(actor)
    if uid is None:
        return WorkflowTask.objects.none()
    role = _role(actor)
    return WorkflowTask.objects.filter(
        Q(assignee_user_id=uid) | Q(assignee_role=role),
        status="pending",
    )


def get_visible_application(actor, pk: int) -> LeaveApplication:
    from core.api.exceptions import NotFoundError

    row = applications_for(actor).filter(pk=pk).first()
    if row is None:
        raise NotFoundError("Leave application not found.")
    return row
