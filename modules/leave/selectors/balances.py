"""Read queries for leave balances and ledger."""
from __future__ import annotations

import datetime
from decimal import InvalidOperation
from django.db.models import QuerySet

from modules.leave.models import LeaveBalance, LeaveLedgerEntry, LeavePolicyConfig


def configured_entitlements() -> dict[str, Decimal]:
    defaults = {"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "VL": 60, "COL": 20}
    row = LeavePolicyConfig.objects.filter(key="policy.entitlements").first()
    values = row.value if row and isinstance(row.value, dict) else {}
    result = {}
    for category, default in defaults.items():
        try:
            result[category] = Decimal(str(values.get(category, default)))
        except (InvalidOperation, TypeError, ValueError):
            result[category] = Decimal(str(default))
    return result


def get_or_create_balance(user_id: int, year: int | None = None, is_faculty: bool = False) -> LeaveBalance:
    """Retrieve or initialize the employee's leave balance for the year."""
    if year is None:
        year = datetime.date.today().year

    entitlements = configured_entitlements()
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        year=year,
        defaults={
            "is_faculty": is_faculty,
            "cl_balance": entitlements["CL"],
            "rh_balance": entitlements["RH"],
            "scl_balance": entitlements["SCL"],
            "el_balance": Decimal("0.0") if is_faculty else entitlements["EL"],
            "vl_balance": entitlements["VL"] if is_faculty else Decimal("0.0"),
            "col_balance": entitlements["COL"],
        },
    )
    return balance


def get_ledger_history(user_id: int, year: int | None = None) -> QuerySet[LeaveLedgerEntry]:
    """Retrieve audit ledger history for an employee."""
    qs = LeaveLedgerEntry.objects.filter(user_id=user_id)
    if year:
        qs = qs.filter(balance__year=year)
    return qs.order_by("-created_at")
