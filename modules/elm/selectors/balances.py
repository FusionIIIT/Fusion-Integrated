"""Leave balances and leave types selectors."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import LeaveBalance, LeaveType


def list_active_leave_types(is_faculty: bool | None = None) -> QuerySet[LeaveType]:
    """Retrieve active leave types, optionally filtered by faculty applicability."""
    qs = LeaveType.objects.filter(is_active=True)
    if is_faculty is True:
        qs = qs.exclude(is_non_faculty_only=True)
    elif is_faculty is False:
        qs = qs.exclude(is_faculty_only=True)
    return qs.order_by("code")


def get_leave_type_by_id(leave_type_id: int) -> LeaveType | None:
    try:
        return LeaveType.objects.get(id=leave_type_id, is_active=True)
    except LeaveType.DoesNotExist:
        return None


def get_leave_type_by_code(code: str) -> LeaveType | None:
    try:
        return LeaveType.objects.get(code=code, is_active=True)
    except LeaveType.DoesNotExist:
        return None


def get_employee_balances(employee_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Retrieve balances for a given employee and year."""
    return LeaveBalance.objects.filter(
        employee_id=employee_id,
        year=year,
    ).select_related("leave_type").order_by("leave_type__code")


def get_employee_balance_or_none(employee_id: int, leave_type: LeaveType, year: int) -> LeaveBalance | None:
    """Retrieve specific balance record or None."""
    try:
        return LeaveBalance.objects.get(employee_id=employee_id, leave_type=leave_type, year=year)
    except LeaveBalance.DoesNotExist:
        return None
