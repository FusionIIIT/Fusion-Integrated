import datetime
from decimal import Decimal

import pytest

from modules.leave.contracts import get_active_leaves, get_leave_balances
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import LeaveRequest, LedgerEntry

pytestmark = pytest.mark.django_db


def test_get_leave_balances_contract():
    uid1 = 501
    uid2 = 502
    year = 2026

    LedgerEntry.objects.create(user_id=uid1, year=year, category="CL", days=Decimal("8.0"), reason="credit")
    LedgerEntry.objects.create(user_id=uid1, year=year, category="EL", days=Decimal("30.0"), reason="credit")
    LedgerEntry.objects.create(user_id=uid2, year=year, category="CL", days=Decimal("5.5"), reason="credit")

    balances = get_leave_balances([uid1, uid2, 999], year=year)

    assert uid1 in balances
    assert balances[uid1]["CL"]["available"] == Decimal("8.00")
    assert balances[uid1]["EL"]["available"] == Decimal("30.00")

    assert uid2 in balances
    assert balances[uid2]["CL"]["available"] == Decimal("5.50")

    # User 999 has no ledger entries -> 0 available balance
    assert balances[999]["CL"]["available"] == Decimal("0.0")


def test_get_active_leaves_contract():
    uid1 = 501
    uid2 = 502
    today = datetime.date(2026, 3, 10)

    # Active leave for uid1 covering today
    LeaveRequest.objects.create(
        user_id=uid1,
        category="CL",
        starts_on=datetime.date(2026, 3, 9),
        ends_on=datetime.date(2026, 3, 11),
        requested_days=Decimal("3.0"),
        reason="Sick leave",
        state=LeaveState.APPROVED,
    )

    # Inactive / future leave for uid2
    LeaveRequest.objects.create(
        user_id=uid2,
        category="EL",
        starts_on=datetime.date(2026, 4, 1),
        ends_on=datetime.date(2026, 4, 10),
        requested_days=Decimal("10.0"),
        reason="Conference",
        state=LeaveState.APPROVED,
    )

    result = get_active_leaves([uid1, uid2, 999], on_date=today)

    assert len(result[uid1]) == 1
    assert result[uid1][0].category == "CL"
    assert result[uid1][0].user_id == uid1

    # uid2 has no leave on today
    assert result[uid2] == []
    # 999 has no leave
    assert result[999] == []
