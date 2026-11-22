from datetime import date
from typing import Sequence
from modules.elm.models import HolidayCalendar, LeaveBalance, LeaveRequest


def get_leave_balances(employee_id: int, year: int | None = None) -> list[LeaveBalance]:
    target_year = year or date.today().year
    return list(LeaveBalance.objects.filter(employee_id=employee_id, year=target_year))


def get_leave_balance(employee_id: int, leave_type: str, year: int | None = None) -> LeaveBalance | None:
    target_year = year or date.today().year
    return LeaveBalance.objects.filter(employee_id=employee_id, leave_type=leave_type, year=target_year).first()


def get_employee_leave_requests(employee_id: int) -> list[LeaveRequest]:
    return list(LeaveRequest.objects.filter(applicant_id=employee_id))


def get_pending_substitute_requests(substitute_id: int) -> list[LeaveRequest]:
    return list(LeaveRequest.objects.filter(substitute_id=substitute_id, substitute_status="PENDING"))


def get_leave_request_by_id(request_id: int) -> LeaveRequest | None:
    return LeaveRequest.objects.filter(id=request_id).first()


def check_date_overlap(employee_id: int, start_date: date, end_date: date, exclude_id: int | None = None) -> bool:
    qs = LeaveRequest.objects.filter(
        applicant_id=employee_id,
        status__in=["PENDING_APPROVAL", "RECOMMENDED", "APPROVED", "PENDING_SUBSTITUTE"],
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()


def get_active_holidays(year: int | None = None) -> set[date]:
    target_year = year or date.today().year
    return set(HolidayCalendar.objects.filter(year=target_year).values_list("date", flat=True))
