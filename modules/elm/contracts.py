"""Public contract surface for modules.elm.
Other modules may only import functions defined here.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from modules.elm.models import LeaveBalance
from modules.elm.selectors.leave import check_date_overlap



def has_active_leave(employee_id: int, on_date: date) -> bool:
    """Returns True if the employee has approved or pending leave on the given date."""
    return check_date_overlap(employee_id, on_date, on_date)



def get_employee_balances(
    employee_ids: Sequence[int], year: int | None = None
) -> dict[int, list[dict]]:
    """Batched query returning leave balances mapped by employee_id."""
    target_year = year or date.today().year
    qs = LeaveBalance.objects.filter(employee_id__in=employee_ids, year=target_year)
    result: dict[int, list[dict]] = {emp_id: [] for emp_id in employee_ids}
    for b in qs:
        result.setdefault(b.employee_id, []).append(
            {
                "leave_type": b.leave_type,
                "year": b.year,
                "allocated": float(b.allocated),
                "availed": float(b.availed),
                "balance": float(b.balance),
            }
        )
    return result
