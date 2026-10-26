"""Cross-module public contract for Employee Leave Management (ELM)."""
from collections.abc import Sequence

from django.utils import timezone

from modules.leave.models import LeaveApplication, LeaveBalance


def get_active_leaves(employee_ids: Sequence[str]) -> list[dict]:
    """Return currently active leaves for a batch of employee ids."""
    today = timezone.localdate()
    qs = LeaveApplication.objects.filter(
        applicant_id__in=employee_ids,
        status=LeaveApplication.STATUS_APPROVED,
        start_date__lte=today,
        end_date__gte=today,
    ).select_related("leave_type")

    return [
        {
            "employee_id": app.applicant_id,
            "leave_type_code": app.leave_type.code,
            "start_date": app.start_date,
            "end_date": app.end_date,
        }
        for app in qs
    ]


def get_leave_balances(employee_ids: Sequence[str]) -> list[dict]:
    """Return annual leave balances for a batch of employee ids."""
    year = timezone.now().year
    qs = LeaveBalance.objects.filter(
        employee_id__in=employee_ids, year=year
    ).select_related("leave_type")

    return [
        {
            "employee_id": b.employee_id,
            "leave_type_code": b.leave_type.code,
            "available": b.available,
        }
        for b in qs
    ]
