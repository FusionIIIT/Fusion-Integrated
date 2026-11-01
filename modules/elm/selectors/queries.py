"""Read queries for Employee Leave Management."""

from datetime import date

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveAccountTransaction,
    LeaveApplication,
    LeaveBalance,
    LeaveNotification,
    SlaConfig,
)


def list_employee_applications(employee_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(employee_id=employee_id).order_by("-created_at")[:100]


def get_employee_application(employee_id: int, pk: int) -> LeaveApplication:
    return get_object_or_404(LeaveApplication, pk=pk, employee_id=employee_id)


def get_accessible_application(actor_id: int, pk: int) -> LeaveApplication:
    """Return application if actor is applicant, substitute, unit head, or authority."""
    return get_object_or_404(
        LeaveApplication.objects.filter(
            Q(employee_id=actor_id)
            | Q(substitute_user_id=actor_id)
            | Q(unit_head_id=actor_id)
            | Q(establishment_id=actor_id)
            | Q(sanction_authority_id=actor_id)
            | Q(approver_id=actor_id)
        ),
        pk=pk,
    )


def list_approval_queue(actor_id: int) -> QuerySet[LeaveApplication]:
    """Return all actionable requests for the given actor across all workflow stages."""
    # 1. Other users' requests assigned to actor
    others_q = (
        Q(status="AWAITING_SUB", substitute_user_id=actor_id, substitute_status="PENDING")
        | Q(status="PENDING", unit_head_id=actor_id)
        | Q(status="AWAITING_ESTABLISHMENT", establishment_id=actor_id)
        | Q(status="RECOMMENDED", sanction_authority_id=actor_id)
        | Q(status="CANCELLATION_PENDING", unit_head_id=actor_id)
        | Q(status="CANCELLATION_ESTABLISHMENT", establishment_id=actor_id)
        | Q(status="CANCELLATION_SANCTION", sanction_authority_id=actor_id)
        | Q(
            status="EXTENSION_AWAITING_SUB",
            substitute_user_id=actor_id,
            substitute_status="PENDING",
        )
        | Q(status="EXTENSION_PENDING", unit_head_id=actor_id)
        | Q(status="EXTENSION_ESTABLISHMENT", establishment_id=actor_id)
        | Q(status="EXTENSION_SANCTION", sanction_authority_id=actor_id)
        | Q(status="RESUMPTION_PENDING", sanction_authority_id=actor_id)
        | Q(status="RESUMPTION_PENDING", unit_head_id=actor_id, sanction_authority_id__isnull=True)
    ) & ~Q(employee_id=actor_id)

    # 2. Director self-sanction (applicant IS the actor)
    director_q = Q(status="AWAITING_DIRECTOR", employee_id=actor_id)

    return LeaveApplication.objects.filter(others_q | director_q).order_by("created_at")[:100]


def list_employee_balances(employee_id: int, year: int) -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.filter(employee_id=employee_id, year=year).order_by("category")


def list_profiles() -> QuerySet[EmployeeLeaveProfile]:
    return EmployeeLeaveProfile.objects.order_by("user_id")[:100]


def list_holidays() -> QuerySet[Holiday]:
    return Holiday.objects.order_by("date")[:200]


def list_notifications(user_id: int) -> QuerySet[LeaveNotification]:
    return LeaveNotification.objects.filter(recipient_id=user_id).order_by("-created_at")[:50]


def list_account_transactions(
    employee_id: int, year: int | None = None
) -> QuerySet[LeaveAccountTransaction]:
    qs = LeaveAccountTransaction.objects.filter(employee_id=employee_id)
    if year:
        qs = qs.filter(year=year)
    return qs.order_by("-created_at")[:100]


def list_sla_configs() -> QuerySet[SlaConfig]:
    return SlaConfig.objects.order_by("task_type")


def get_published_dates(start: date, end: date, kind: str) -> frozenset[date]:
    return frozenset(
        Holiday.objects.filter(date__range=(start, end), kind=kind, published=True).values_list(
            "date", flat=True
        )
    )
