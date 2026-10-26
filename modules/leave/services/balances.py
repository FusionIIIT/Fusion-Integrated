"""Balance management service for Leave Management."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from modules.leave.domain.entities import LeaveType
from modules.leave.domain.rules import calculate_balance_deduction
from modules.leave.models import LeaveBalance

DEFAULT_QUOTAS: dict[str, Decimal] = {
    LeaveType.CASUAL.value: Decimal("12.0"),
    LeaveType.RESTRICTED.value: Decimal("2.0"),
    LeaveType.MEDICAL.value: Decimal("10.0"),
    LeaveType.EARNED.value: Decimal("30.0"),
    LeaveType.VACATION.value: Decimal("60.0"),
    LeaveType.SABBATICAL.value: Decimal("365.0"),
}


def ensure_balances_for_user(user_id: int, year: int | None = None) -> list[LeaveBalance]:
    """Ensure that standard leave balances are provisioned for the given user and year."""
    target_year = year or date.today().year
    balances = []
    with transaction.atomic():
        for l_type, quota in DEFAULT_QUOTAS.items():
            bal, _ = LeaveBalance.objects.get_or_create(
                user_id=user_id,
                leave_type=l_type,
                year=target_year,
                defaults={
                    "total_entitlement": quota,
                    "consumed_days": Decimal("0.0"),
                    "available_balance": quota,
                },
            )
            balances.append(bal)
    return balances


def deduct_leave_balance(
    user_id: int,
    leave_type: str,
    days: Decimal,
    year: int | None = None,
) -> LeaveBalance:
    """Apply automatic leave balance deduction upon approval per BR-HR-010."""
    target_year = year or date.today().year
    ensure_balances_for_user(user_id, target_year)

    bal = LeaveBalance.objects.select_for_update().get(
        user_id=user_id,
        leave_type=leave_type,
        year=target_year,
    )

    new_consumed, new_available = calculate_balance_deduction(
        bal.consumed_days,
        bal.available_balance,
        days,
    )
    bal.consumed_days = new_consumed
    bal.available_balance = new_available
    bal.save(update_fields=["consumed_days", "available_balance", "updated_at"])
    return bal
