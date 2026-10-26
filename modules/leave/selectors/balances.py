"""Leave balance query selectors."""

from django.db.models import QuerySet

from modules.leave.models import LeaveBalance, LeaveTypeConfig


def list_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Return all leave balances for a specific user and year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("leave_type")


def get_user_balance(user_id: int, year: int, leave_type: str) -> LeaveBalance | None:
    """Return a single leave balance object or None."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year, leave_type=leave_type).first()


def list_leave_types(applies_to: str | None = None) -> QuerySet[LeaveTypeConfig]:
    """Return configured leave types."""
    qs = LeaveTypeConfig.objects.all().order_by("code")
    if applies_to and applies_to != "all":
        qs = qs.filter(applies_to__in=["all", applies_to])
    return qs
