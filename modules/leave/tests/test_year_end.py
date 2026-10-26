# Tests for annual leave rollover command (BR-EL-002..008)
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from modules.leave.domain.constants import (
    LEAVE_TYPE_CL,
    LEAVE_TYPE_COL,
    LEAVE_TYPE_EL,
    LEAVE_TYPE_RH,
    LEAVE_TYPE_SCL,
    LEAVE_TYPE_VL,
)
from modules.leave.models import LeaveBalance

pytestmark = pytest.mark.django_db


def test_year_end_rollover():
    """BR-EL-002..008: Lapses CL/RH/SCL, carries over EL/COL, converts VL to EL at 2:1."""
    user_id = 701
    year = 2026
    next_year = 2027

    # Create balances for year 2026:
    # CL: 8 allocated, 3 used -> 5 unused (should lapse)
    LeaveBalance.objects.create(user_id=user_id, leave_type=LEAVE_TYPE_CL, year=year, allocated=Decimal("8.00"), used=Decimal("3.00"))
    # RH: 2 allocated, 1 used -> 1 unused (should lapse)
    LeaveBalance.objects.create(user_id=user_id, leave_type=LEAVE_TYPE_RH, year=year, allocated=Decimal("2.00"), used=Decimal("1.00"))
    # SCL: 15 allocated, 5 used -> 10 unused (should lapse)
    LeaveBalance.objects.create(user_id=user_id, leave_type=LEAVE_TYPE_SCL, year=year, allocated=Decimal("15.00"), used=Decimal("5.00"))
    # EL: 30 allocated, 10 used -> 20 unused (carries over: 30 + 20 = 50 + VL conversion)
    LeaveBalance.objects.create(user_id=user_id, leave_type=LEAVE_TYPE_EL, year=year, allocated=Decimal("30.00"), used=Decimal("10.00"))
    # COL: 20 allocated, 5 used -> 15 unused (carries over: 20 + 15 = 35)
    LeaveBalance.objects.create(user_id=user_id, leave_type=LEAVE_TYPE_COL, year=year, allocated=Decimal("20.00"), used=Decimal("5.00"))
    # VL: 60 allocated, 45 used -> 15 unused (converts 15/2 = 7.5 EL, VL resets to 60)
    LeaveBalance.objects.create(user_id=user_id, leave_type=LEAVE_TYPE_VL, year=year, allocated=Decimal("60.00"), used=Decimal("45.00"))

    out = StringIO()
    call_command("process_leave_year_end", year=year, next_year=next_year, stdout=out)

    # Verify next year balances
    bal_cl = LeaveBalance.objects.get(user_id=user_id, leave_type=LEAVE_TYPE_CL, year=next_year)
    assert bal_cl.allocated == Decimal("8.00")
    assert bal_cl.used == Decimal("0.00")

    bal_rh = LeaveBalance.objects.get(user_id=user_id, leave_type=LEAVE_TYPE_RH, year=next_year)
    assert bal_rh.allocated == Decimal("2.00")
    assert bal_rh.used == Decimal("0.00")

    bal_scl = LeaveBalance.objects.get(user_id=user_id, leave_type=LEAVE_TYPE_SCL, year=next_year)
    assert bal_scl.allocated == Decimal("15.00")
    assert bal_scl.used == Decimal("0.00")

    bal_col = LeaveBalance.objects.get(user_id=user_id, leave_type=LEAVE_TYPE_COL, year=next_year)
    # 20 standard + 15 carried over = 35
    assert bal_col.allocated == Decimal("35.00")
    assert bal_col.used == Decimal("0.00")

    bal_vl = LeaveBalance.objects.get(user_id=user_id, leave_type=LEAVE_TYPE_VL, year=next_year)
    # Resets to standard 60
    assert bal_vl.allocated == Decimal("60.00")
    assert bal_vl.used == Decimal("0.00")

    bal_el = LeaveBalance.objects.get(user_id=user_id, leave_type=LEAVE_TYPE_EL, year=next_year)
    # 30 standard + 20 carried over EL + 7.5 converted from VL = 57.50
    assert bal_el.allocated == Decimal("57.50")
    assert bal_el.used == Decimal("0.00")
