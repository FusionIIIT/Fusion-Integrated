"""Public contract surface for modules.elm.
Other modules may only import functions defined here.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from modules.elm.models import LeaveRequest
from modules.elm.selectors.leave import get_leave_balances, check_date_overlap


def has_active_leave(employee_id: int, on_date: date) -> bool:
    """Returns True if the employee has approved or pending leave on the given date."""
    return check_date_overlap(employee_id, on_date, on_date)


def get_employee_balances(employee_id: int, year: int | None = None) -> list[dict]:
    balances = get_leave_balances(employee_id, year)
    return [
        {
            "leave_type": b.leave_type,
            "year": b.year,
            "allocated": float(b.allocated),
            "availed": float(b.availed),
            "balance": float(b.balance),
        }
        for b in balances
    ]
