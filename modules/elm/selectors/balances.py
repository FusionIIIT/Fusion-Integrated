"""Read-only selectors for leave balances."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models.balances import LeaveAccountTransaction, LeaveBalance


def get_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Retrieve all category balances for a user in a given calendar year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")


def get_user_balance_for_category(user_id: int, year: int, category: str) -> LeaveBalance | None:
    """Retrieve a single category balance for a user in a given year."""
    try:
        return LeaveBalance.objects.get(user_id=user_id, year=year, category=category)
    except LeaveBalance.DoesNotExist:
        return None


def get_user_transactions(user_id: int, year: int) -> QuerySet[LeaveAccountTransaction]:
    """Retrieve balance transactions ledger for a user in a given year."""
    return LeaveAccountTransaction.objects.filter(user_id=user_id, year=year).order_by("-created_at")
