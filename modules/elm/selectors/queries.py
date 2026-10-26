"""Read queries for Employee Leave Management."""

from datetime import date

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from modules.elm.domain.policy import is_director
from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveApplication,
    LeaveBalance,
)


def list_employee_applications(employee_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(employee_id=employee_id).order_by("-created_at")[:100]


def get_employee_application(employee_id: int, pk: int) -> LeaveApplication:
    return get_object_or_404(LeaveApplication, pk=pk, employee_id=employee_id)


def list_approval_queue(actor: int | object) -> QuerySet[LeaveApplication]:
    actor_id = getattr(actor, "user_id", actor)
    profile = EmployeeLeaveProfile.objects.filter(user_id=actor_id).first()
    is_dir = profile is not None and is_director(profile.designation)
    base_q = (
        Q(status="AWAITING_SUB", substitute_user_id=actor_id, substitute_status="PENDING")
        | Q(status="PENDING", unit_head_id=actor_id)
        | Q(status="RECOMMENDED", sanction_authority_id=actor_id)
        | Q(status="AWAITING_CANCEL", category__in=["CL", "RH"], unit_head_id=actor_id)
        | Q(
            status="AWAITING_CANCEL",
            category__in=["EL", "COL", "VL", "SCL"],
            unit_head_id=actor_id,
            recommendation="",
        )
        | (
            Q(
                status="AWAITING_CANCEL",
                category__in=["EL", "COL", "VL", "SCL"],
                sanction_authority_id=actor_id,
            )
            & Q(recommendation__in=["RECOMMENDED", "NOT_RECOMMENDED"])
        )
        | Q(status="AWAITING_RESUMPTION", sanction_authority_id=actor_id)
    )
    if is_dir:
        base_q |= Q(status="AWAITING_CANCEL", employee_id=actor_id)
        base_q |= Q(status="AWAITING_RESUMPTION", employee_id=actor_id)
        return LeaveApplication.objects.filter(base_q).order_by("created_at")[:100]
    return (
        LeaveApplication.objects.filter(base_q)
        .exclude(employee_id=actor_id)
        .order_by("created_at")[:100]
    )


def list_employee_balances(employee_id: int, year: int) -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.filter(employee_id=employee_id, year=year).order_by("category")


def list_profiles() -> QuerySet[EmployeeLeaveProfile]:
    return EmployeeLeaveProfile.objects.order_by("user_id")[:100]


def list_holidays() -> QuerySet[Holiday]:
    return Holiday.objects.order_by("date")[:200]


def get_published_dates(start: date, end: date, kind: str) -> frozenset[date]:
    return frozenset(
        Holiday.objects.filter(date__range=(start, end), kind=kind, published=True).values_list(
            "date", flat=True
        )
    )
