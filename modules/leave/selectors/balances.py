"""Selectors for Leave Balances."""
from datetime import date
from typing import Optional

from django.db.models import QuerySet

from ..models import LeaveBalance
from ..domain.entities import LeaveCategory, EmployeeType


def get_or_create_balance(user_id: int, category: str, year: int) -> LeaveBalance:
    """Get or create leave balance for user, category, year."""
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        category=category,
        year=year,
        defaults={
            "opening_balance": 0,
            "credited": 0,
            "availed": 0,
            "lapsed": 0,
            "closing_balance": 0,
        },
    )
    return balance


def get_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Get all leave balances for a user in a year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_all_user_balances(user_id: int) -> QuerySet[LeaveBalance]:
    """Get all leave balances for a user across all years."""
    return LeaveBalance.objects.filter(user_id=user_id).order_by("-year", "category")


def get_balances_for_category(category: str, year: int) -> QuerySet[LeaveBalance]:
    """Get all user balances for a specific category and year."""
    return LeaveBalance.objects.filter(category=category, year=year).select_related()


def calculate_vl_to_el_conversion(vl_balance: float) -> float:
    """Calculate EL credited from VL conversion (2 VL = 1 EL)."""
    return vl_balance / 2.0