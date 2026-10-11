"""Leave balance selectors.

Calculates balances dynamically from the append-only ledger.
"""
from decimal import Decimal

from django.db.models import Sum

from modules.leave.domain.constants import LeaveCategory
from modules.leave.models.ledger import LeaveLedgerEntry


def get_user_balances(user_id: int) -> dict[str, Decimal]:
    """Computes real-time leave balances for a user across all 6 categories."""
    entries = (
        LeaveLedgerEntry.objects.filter(user_id=user_id)
        .values("category")
        .annotate(total=Sum("delta_days"))
    )
    totals = {e["category"]: e["total"] or Decimal("0.0") for e in entries}

    return {
        cat.value: totals.get(cat.value, Decimal("0.0"))
        for cat in LeaveCategory
    }


def get_category_balance(user_id: int, category: str) -> Decimal:
    """Returns balance for a specific category."""
    total = (
        LeaveLedgerEntry.objects.filter(user_id=user_id, category=category)
        .aggregate(total=Sum("delta_days"))["total"]
    )
    return total or Decimal("0.0")
