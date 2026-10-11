"""Selectors for leave module (reads and ownership filtering)."""
from typing import Optional, List
from django.db.models import QuerySet
from modules.leave.models import LeaveApplication, LeaveBalance, HolidayCalendar, LeavePolicy


def get_employee_applications(applicant_id: str) -> QuerySet[LeaveApplication]:
    """Inquiry: employee's own requests (EL-UC-012, CFR-EL-022)."""
    return LeaveApplication.objects.filter(applicant_id=applicant_id).order_by("-created_at")


def get_employee_balances(user_id: str, year: int) -> QuerySet[LeaveBalance]:
    """Inquiry: employee's current balances (EL-UC-012, AFR-EL-022.1)."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_substitute_pending_requests(substitute_id: str) -> QuerySet[LeaveApplication]:
    """Substitute review work queue (EL-UC-002)."""
    return LeaveApplication.objects.filter(
        substitute_id=substitute_id,
        status="AWAITING_SUBSTITUTE"
    )


def get_unit_head_pending_requests(unit_head_id: str) -> QuerySet[LeaveApplication]:
    """Unit head review queue (EL-UC-003, CW-EL-01, CW-EL-02, CW-EL-03)."""
    return LeaveApplication.objects.filter(
        unit_head_id=unit_head_id,
        status__in=["AWAITING_UNIT_HEAD", "CANCELLATION_PENDING_UH"]
    )


def get_sanctioning_queue(sanctioning_id: Optional[str] = None) -> QuerySet[LeaveApplication]:
    """Final sanctioning authority queue (EL-UC-005)."""
    qs = LeaveApplication.objects.filter(
        status__in=["AWAITING_SANCTION", "AWAITING_DIRECTOR", "CANCELLATION_PENDING_SANCTION", "RESUMPTION_PENDING"]
    )
    if sanctioning_id:
        qs = qs.filter(sanctioning_authority_id=sanctioning_id)
    return qs
