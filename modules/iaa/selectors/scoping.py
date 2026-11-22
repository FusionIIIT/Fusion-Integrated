"""Who sees which rows (BR-501, BR-004). Out-of-scope rows are absent, so detail views 404."""
from __future__ import annotations

from django.db.models import Exists, OuterRef, Q, QuerySet

from modules.directory import contracts as directory
from modules.iaa.domain import roles
from modules.iaa.models import (
    Anomaly,
    ApprovalStep,
    AuditObservation,
    FinancialRecord,
    Notification,
)

_OFFICE_WIDE = frozenset({roles.FINANCE, roles.AUDITOR})


def _role(actor) -> str | None:
    return getattr(actor, "active_role", None)


def _department(actor) -> str:
    user = directory.get_users([actor.user_id]).get(actor.user_id)
    return (user.department if user else "") or ""


def _assigned_steps(actor) -> QuerySet[ApprovalStep]:
    role = _role(actor)
    steps = ApprovalStep.objects.filter(designation=role)
    if role in roles.DEPARTMENT_SCOPED:
        department = _department(actor)
        if not department:
            return steps.none()
        steps = steps.filter(record__department=department)
    return steps


def records_for(actor) -> QuerySet[FinancialRecord]:
    qs = FinancialRecord.objects.all()
    if actor is None:
        return qs.none()
    role = _role(actor)
    if role in _OFFICE_WIDE:
        return qs.exclude(status="draft")
    if role == roles.SYSTEM_ADMIN:
        return qs.none()
    if role in roles.APPROVERS:
        return qs.filter(Exists(_assigned_steps(actor).filter(record=OuterRef("pk"))))
    return qs.filter(user_id=actor.user_id)


def pending_steps_for(actor) -> QuerySet[ApprovalStep]:
    if actor is None or _role(actor) not in roles.APPROVERS:
        return ApprovalStep.objects.none()
    return _assigned_steps(actor).filter(status=ApprovalStep.PENDING)


def anomalies_for(actor) -> QuerySet[Anomaly]:
    qs = Anomaly.objects.all()
    if actor is None:
        return qs.none()
    role = _role(actor)
    if role in _OFFICE_WIDE:
        return qs
    if role in roles.APPROVERS:
        return qs.filter(Q(assigned_role=role) | Q(resolved_role=role))
    return qs.none()


def observations_for(actor) -> QuerySet[AuditObservation]:
    qs = AuditObservation.objects.all()
    if actor is None:
        return qs.none()
    role = _role(actor)
    if role in _OFFICE_WIDE:
        return qs
    if role == roles.SYSTEM_ADMIN or role in roles.APPROVERS:
        return qs.none()
    return qs.filter(respondent_user_id=actor.user_id)


def notifications_for(actor) -> QuerySet[Notification]:
    if actor is None:
        return Notification.objects.none()
    role = _role(actor)
    if role == roles.SYSTEM_ADMIN:
        return Notification.objects.none()
    q = Q(recipient_role=role) if role else Q(pk__in=[])
    if role not in roles.APPROVERS and role not in _OFFICE_WIDE:
        q |= Q(recipient_user_id=actor.user_id)
    return Notification.objects.filter(q)
