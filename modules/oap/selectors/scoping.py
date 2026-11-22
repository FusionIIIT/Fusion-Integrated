"""Row visibility, decided once here. Anything out of scope is absent (404, never 403).

Permissions decide the verb; the acting role decides the rows a responsible
office sees. A missing or unknown role fails closed to no rows.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.oap.domain import roles
from modules.oap.domain import state_machines as sm
from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    LeaveApplication,
    NoDuesCase,
    SeminarRequest,
    SeminarSchedule,
)

#: Matches every row. Never Q(): an empty Q combined with OR narrows, not widens.
ALL = Q(pk__isnull=False)


def _union(model, *clauses: Q | None) -> QuerySet:
    present = [c for c in clauses if c is not None]
    if not present:
        return model.objects.none()
    combined = present[0]
    for clause in present[1:]:
        combined = combined | clause
    return model.objects.filter(combined)


def _when(condition: bool, clause: Q) -> Q | None:
    return clause if condition else None


def _has(principal, code: str) -> bool:
    return principal.has_permission(code)


def leave_for(principal) -> QuerySet:
    return _union(
        LeaveApplication,
        _when(_has(principal, "oap.leave_application.view_self"), Q(user_id=principal.user_id)),
        _when(
            principal.active_role == roles.HOD and _has(principal, "oap.leave_application.view"),
            ALL,
        ),
    )


def bonafide_for(principal) -> QuerySet:
    return _union(
        BonafideRequest,
        _when(_has(principal, "oap.bonafide_request.view_self"), Q(user_id=principal.user_id)),
        _when(
            principal.active_role == roles.ACADEMIC_ADMIN
            and _has(principal, "oap.bonafide_request.view"),
            ALL,
        ),
    )


def no_dues_for(principal) -> QuerySet:
    authority = principal.active_role in roles.AUTHORITY_DOMAIN
    can_view = _has(principal, "oap.no_dues_case.view")
    return _union(
        NoDuesCase,
        _when(_has(principal, "oap.no_dues_case.view_self"), Q(user_id=principal.user_id)),
        _when(principal.active_role == roles.ACADEMIC_ADMIN and can_view, ALL),
        _when(authority and can_view, ALL),
    )


def claims_for(principal) -> QuerySet:
    can_view = _has(principal, "oap.assistantship_claim.view")
    hod_stages = [
        sm.CLAIM_AWAITING_HOD,
        sm.CLAIM_APPROVED,
        sm.CLAIM_REJECTED,
        sm.CLAIM_STIPEND_PROCESSED,
    ]
    supervisor = None
    if _has(principal, "oap.assistantship_verification.review"):
        supervisor = Q(thesis_supervisor_user_id=principal.user_id) | Q(
            ta_supervisor_user_id=principal.user_id
        )
    return _union(
        AssistantshipClaim,
        _when(_has(principal, "oap.assistantship_claim.view_self"), Q(user_id=principal.user_id)),
        _when(principal.active_role == roles.DEPARTMENT_ADMIN and can_view, ALL),
        _when(principal.active_role == roles.HOD and can_view, Q(status__in=hod_stages)),
        _when(
            principal.active_role == roles.ACADEMIC_ADMIN and can_view,
            Q(status__in=[sm.CLAIM_APPROVED, sm.CLAIM_STIPEND_PROCESSED]),
        ),
        supervisor,
    )


def seminar_requests_for(principal) -> QuerySet:
    return _union(
        SeminarRequest,
        _when(_has(principal, "oap.seminar_request.view_self"), Q(user_id=principal.user_id)),
        _when(
            principal.active_role == roles.DEPARTMENT_ADMIN
            and _has(principal, "oap.seminar_request.view"),
            ALL,
        ),
    )


def seminar_schedules_for(principal) -> QuerySet:
    if not _has(principal, "oap.seminar_schedule.view"):
        return SeminarSchedule.objects.none()
    return SeminarSchedule.objects.all()
