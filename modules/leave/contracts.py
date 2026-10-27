"""Inter-module public contracts for Employee Leave Management."""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional


def is_user_on_leave(user_id: int, on_date: Optional[datetime.date] = None) -> bool:
    """Check if an employee is on approved leave on the given date (default today)."""
    from modules.leave.models import LeaveApplication
    check_date = on_date or datetime.date.today()
    return LeaveApplication.objects.filter(
        user_id=user_id,
        status="approved",
        start_date__lte=check_date,
        end_date__gte=check_date,
    ).exists()


def get_active_leave(user_id: int, on_date: Optional[datetime.date] = None):
    """Return the active approved LeaveApplication for an employee on a given date."""
    from modules.leave.models import LeaveApplication
    check_date = on_date or datetime.date.today()
    return LeaveApplication.objects.filter(
        user_id=user_id,
        status="approved",
        start_date__lte=check_date,
        end_date__gte=check_date,
    ).first()


def get_leave_balances(user_id: int, year: Optional[int] = None) -> dict[str, Decimal]:
    """Return a summary dict of current leave balances for an employee."""
    from modules.leave.models import LeaveBalance
    target_year = year or datetime.date.today().year
    bal = LeaveBalance.objects.filter(user_id=user_id, year=target_year).first()
    if not bal:
        return {}
    return {
        "cl": bal.cl_balance,
        "rh": bal.rh_balance,
        "scl": bal.scl_balance,
        "el": bal.el_balance,
        "vl": bal.vl_balance,
        "col": bal.col_balance,
    }
