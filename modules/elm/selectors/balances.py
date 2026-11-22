"""Leave balance and account selectors for ELM."""
from __future__ import annotations

from decimal import Decimal

from modules.elm.models import LeaveAccount, LeaveBalanceTransaction


def get_balances_for_user(user_id: int, year: int) -> dict[str, Decimal]:
    """Return dictionary of category -> balance for a user and year."""
    accounts = LeaveAccount.objects.filter(user_id=user_id, year=year)
    return {acc.category: acc.balance for acc in accounts}


def get_leave_account(user_id: int, year: int, category: str) -> LeaveAccount | None:
    """Return specific leave account for a user, year, and category."""
    return LeaveAccount.objects.filter(user_id=user_id, year=year, category=category).first()


def get_balance_history(user_id: int, year: int | None = None) -> list[LeaveBalanceTransaction]:
    """Return balance transactions for a user."""
    qs = LeaveBalanceTransaction.objects.filter(user_id=user_id)
    if year:
        qs = qs.filter(year=year)
    return list(qs.order_by("-created_at"))
