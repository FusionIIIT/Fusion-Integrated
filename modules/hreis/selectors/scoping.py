"""Every HR-EIS read starts with active-role and row-level narrowing."""

from __future__ import annotations

from django.db.models import F, Q, QuerySet

from modules.hreis.domain.routing import AUTHORITY_DESIGNATIONS
from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRRequest,
    Notification,
)

MODULE = "hreis"
HR_ADMIN = "hradmin"
SELF_ROLES = frozenset({"faculty", "staff"})
P_RECORD_VIEW = "hreis.service_record.view"
P_REQUEST_VIEW = "hreis.request.view"
P_NOTIFICATION_VIEW = "hreis.notification.view"
P_AUDIT_VIEW = "hreis.audit.view"


def _valid(actor, permission: str) -> bool:
    return (
        actor is not None
        and getattr(actor, "user_id", None) is not None
        and getattr(actor, "active_role", None) is not None
        and callable(getattr(actor, "has_module", None))
        and actor.has_module(MODULE)
        and callable(getattr(actor, "has_permission", None))
        and actor.has_permission(permission)
    )


def service_records_for(actor) -> QuerySet[EmployeeServiceRecord]:
    base = EmployeeServiceRecord.objects.all()
    if not _valid(actor, P_RECORD_VIEW):
        return base.none()
    if actor.active_role == HR_ADMIN:
        return base
    if actor.active_role in SELF_ROLES | AUTHORITY_DESIGNATIONS | {"Accounts Admin"}:
        return base.filter(user_id=actor.user_id)
    return base.none()


def requests_for(actor) -> QuerySet[HRRequest]:
    base = HRRequest.objects.all()
    if not _valid(actor, P_REQUEST_VIEW):
        return base.none()
    if actor.active_role == HR_ADMIN:
        return base.exclude(user_id=actor.user_id).filter(
            Q(family__in=["ltc", "cpda"], state="awaiting_hr_verification")
            | Q(family="appraisal", state="submitted")
        )
    if actor.active_role in SELF_ROLES:
        return base.filter(user_id=actor.user_id)
    if actor.active_role == "Accounts Admin" and (
        actor.has_permission("hreis.finance.review") or actor.has_permission("hreis.finance.update")
    ):
        return base.filter(
            family__in=["ltc", "cpda"],
            state__in=["approved", "financial_processing_recorded"],
        ).exclude(user_id=actor.user_id)
    if actor.active_role in AUTHORITY_DESIGNATIONS:
        # A matching route step is necessary, but not enough: the actor also
        # needs the family-specific decision permission.
        permitted = Q(pk__in=[])
        if actor.has_permission("hreis.leave.approve"):
            permitted |= Q(family="leave", state="pending_authority")
        if actor.has_permission("hreis.claim.approve"):
            permitted |= Q(family__in=["ltc", "cpda"], state="pending_authority")
        if actor.has_permission("hreis.appraisal.approve"):
            permitted |= Q(
                family="appraisal",
                state__in=["pending_review", "pending_next_appraisal_authority"],
            ) & (
                Q(route_step__gt=0)
                | Q(route_step=0, appraisal__reviewer_user_ids__contains=[actor.user_id])
            )
        return (
            base.exclude(user_id=actor.user_id)
            .filter(
                authority_steps__designation=actor.active_role,
                authority_steps__position=F("route_step"),
            )
            .filter(permitted)
            .distinct()
        )
    return base.none()


def compliance_requests_for(actor) -> QuerySet[HRRequest]:
    """Read-only HR compliance scope; no form payload is exposed by its API serializer."""
    base = HRRequest.objects.all()
    if not _valid(actor, P_AUDIT_VIEW) or actor.active_role != HR_ADMIN:
        return base.none()
    return base


def notifications_for(actor) -> QuerySet[Notification]:
    base = Notification.objects.all()
    if not _valid(actor, P_NOTIFICATION_VIEW):
        return base.none()
    # A request-linked reminder follows its current acting-role assignment. A
    # notification grant may show the generic reminder without granting form access.
    assigned = HRRequest.objects.none()
    if actor.active_role == HR_ADMIN:
        assigned = HRRequest.objects.exclude(user_id=actor.user_id).filter(
            Q(family__in=["ltc", "cpda"], state="awaiting_hr_verification")
            | Q(family="appraisal", state="submitted")
        )
    elif actor.active_role in AUTHORITY_DESIGNATIONS:
        assigned = HRRequest.objects.exclude(user_id=actor.user_id).filter(
            authority_steps__designation=actor.active_role,
            authority_steps__position=F("route_step"),
            state__in=["pending_authority", "pending_review", "pending_next_appraisal_authority"],
        ).filter(
            Q(family__in=["leave", "ltc", "cpda"])
            | Q(route_step__gt=0)
            | Q(appraisal__reviewer_user_ids__contains=[actor.user_id])
        )
    return base.filter(recipient_user_id=actor.user_id).filter(
        Q(request__isnull=True)
        | Q(request__user_id=actor.user_id)
        | Q(request_id__in=requests_for(actor).values("pk"))
        | Q(request_id__in=assigned.values("pk"))
    )


def audit_events_for(actor) -> QuerySet[AuditEvent]:
    base = AuditEvent.objects.all()
    if not _valid(actor, P_AUDIT_VIEW) or actor.active_role != HR_ADMIN:
        return base.none()
    return base
