"""Balance derivation from append-only ledger entries."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from modules.leave.models import LedgerEntry


def get_user_balance(user_id: int, year: int, category: str) -> Decimal:
    """Returns net available balance for user, year, and category."""
    return LedgerEntry.objects.filter(user_id=user_id, year=year, category=category).aggregate(
        total=Sum("days")
    )["total"] or Decimal("0.0")


def get_user_balances_summary(user_id: int, year: int) -> dict[str, dict[str, Decimal]]:
    """Summarizes leave balances by category."""
    entries = LedgerEntry.objects.filter(user_id=user_id, year=year)
    categories = ["CL", "RH", "SCL", "EL", "COL", "VL"]
    out: dict[str, dict[str, Decimal]] = {
        cat: {
            "available": Decimal("0.0"),
            "credited": Decimal("0.0"),
            "consumed": Decimal("0.0"),
            "restored": Decimal("0.0"),
        }
        for cat in categories
    }

    for e in entries:
        cat_data = out.setdefault(
            e.category,
            {
                "available": Decimal("0.0"),
                "credited": Decimal("0.0"),
                "consumed": Decimal("0.0"),
                "restored": Decimal("0.0"),
            },
        )
        cat_data["available"] += e.days
        if e.days > Decimal("0"):
            if e.reason in ("annual_credit", "vl_to_el_conversion"):
                cat_data["credited"] += e.days
            else:
                cat_data["restored"] += e.days
        else:
            cat_data["consumed"] += abs(e.days)

    return out
