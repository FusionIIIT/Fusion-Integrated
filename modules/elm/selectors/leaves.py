"""Leave application selectors for ELM."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.elm.domain.constants import ApplicationStatus
from modules.elm.domain.validation import ExistingLeaveInterval
from modules.elm.models import LeaveApplication, LeaveAuditLog


def get_user_applications(
    user_id: int,
    year: int | None = None,
    status: str | None = None,
) -> QuerySet[LeaveApplication]:
    """Return applications created by a user."""
    qs = LeaveApplication.objects.filter(user_id=user_id)
    if year:
        qs = qs.filter(start_date__year=year)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_application_by_id(application_id: int) -> LeaveApplication | None:
    """Return application by ID without ownership filtering."""
    return LeaveApplication.objects.filter(id=application_id).first()


def get_application_for_user(
    application_id: int,
    user_id: int,
    *,
    is_admin: bool = False,
    is_reviewer: bool = False,
) -> LeaveApplication | None:
    """Return application if user is owner, assigned reviewer/substitute, or admin."""
    app = get_application_by_id(application_id)
    if not app:
        return None

    if is_admin:
        return app

    # Owner
    if app.user_id == user_id:
        return app

    # Substitute
    if app.substitute_user_id == user_id:
        return app

    # Reviewer in the hierarchy
    if is_reviewer and user_id in (
        app.unit_head_user_id,
        app.establishment_user_id,
        app.sanctioning_authority_user_id,
    ):
        return app

    return None


def get_active_or_pending_leaves_for_user(user_id: int) -> list[ExistingLeaveInterval]:
    """Return active pending or approved leave intervals for overlap validation (BR-EL-012)."""
    # Exclude terminal/non-active states: rejected, withdrawn, cancelled
    excluded_states = [
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.WITHDRAWN.value,
        ApplicationStatus.CANCELLED.value,
    ]
    apps = LeaveApplication.objects.filter(
        user_id=user_id
    ).exclude(status__in=excluded_states)

    return [
        ExistingLeaveInterval(
            start_date=a.start_date,
            end_date=a.end_date,
            is_half_day=a.is_half_day,
            half_day_session=a.half_day_session,
            status=a.status,
            category=a.category,
        )
        for a in apps
    ]


def get_substitute_active_leaves(substitute_user_id: int) -> list[ExistingLeaveInterval]:
    """Return active pending or approved leave intervals for a substitute (BR-EL-014)."""
    return get_active_or_pending_leaves_for_user(substitute_user_id)


def list_applications_for_review(
    user_id: int,
    role: str,
) -> QuerySet[LeaveApplication]:
    """List applications currently awaiting review by the given user and role."""
    if role == "unit_head":
        return LeaveApplication.objects.filter(
            unit_head_user_id=user_id,
            status__in=[
                ApplicationStatus.AWAITING_UNIT_HEAD.value,
                ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD.value,
            ],
        ).order_by("created_at")

    if role == "establishment":
        return LeaveApplication.objects.filter(
            Q(establishment_user_id=user_id) | Q(establishment_user_id__isnull=True),
            status__in=[
                ApplicationStatus.AWAITING_ESTABLISHMENT.value,
                ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT.value,
            ],
        ).order_by("created_at")

    if role in ("sanctioning", "dean", "registrar", "director"):
        return LeaveApplication.objects.filter(
            sanctioning_authority_user_id=user_id,
            status__in=[
                ApplicationStatus.AWAITING_FINAL_DECISION.value,
                ApplicationStatus.AWAITING_DIRECTOR.value,
                ApplicationStatus.CANCELLATION_PENDING_FINAL.value,
            ],
        ).order_by("created_at")

    return LeaveApplication.objects.none()


def get_application_audit_logs(application_id: int) -> list[LeaveAuditLog]:
    """Return audit history for a leave application."""
    return list(
        LeaveAuditLog.objects.filter(leave_application_id=application_id).order_by("created_at")
    )
