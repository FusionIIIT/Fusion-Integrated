from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.leave_elm.models import (
    LeaveBalance,
    LeaveBalanceTransaction,
    LeaveCategory,
    YearEndProcessingRun,
)


@pytest.mark.django_db
def test_year_end_lapses_carries_and_converts_once():
    categories = {
        code: LeaveCategory.objects.create(
            code=code,
            name=name,
            annual_entitlement=Decimal(entitlement),
            carry_forward=carry_forward,
        )
        for code, name, entitlement, carry_forward in [
            ("CL", "Casual Leave", "8", False),
            ("EL", "Earned Leave", "30", True),
            ("COL", "Commuted Leave", "20", True),
            ("VL", "Vacation Leave", "60", False),
        ]
    }
    for code, balance in {"CL": "2", "EL": "5", "COL": "4", "VL": "3"}.items():
        LeaveBalance.objects.create(
            user_id=10, category=categories[code], year=2026, closing_balance=Decimal(balance)
        )
    LeaveBalance.objects.create(
        user_id=10,
        category=categories["EL"],
        year=2027,
        opening_balance=0,
        credited=0,
        closing_balance=0,
    )

    call_command("process_leave_year_end", 2026)

    assert (
        LeaveBalance.objects.get(user_id=10, category=categories["CL"], year=2026).closing_balance
        == 0
    )
    earned = LeaveBalance.objects.get(user_id=10, category=categories["EL"], year=2027)
    assert earned.opening_balance == Decimal("5")
    assert earned.credited == Decimal("31.5")
    assert earned.closing_balance == Decimal("36.5")
    assert (
        LeaveBalance.objects.get(user_id=10, category=categories["VL"], year=2026).closing_balance
        == 0
    )
    assert (
        LeaveBalanceTransaction.objects.filter(
            balance__user_id=10, transaction_type="conversion"
        ).count()
        == 2
    )
    assert YearEndProcessingRun.objects.filter(year=2026).exists()

    with pytest.raises(CommandError):
        call_command("process_leave_year_end", 2026)
