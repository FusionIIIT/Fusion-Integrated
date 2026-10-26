from decimal import Decimal

import pytest

from modules.elm.models import LeaveBalance
from modules.elm.services.balances import execute_year_end_processing


@pytest.mark.django_db
def test_year_end_processing_lapse_and_vl_conversion():
    """EL-UC-020, BR-EL-002..008: Year end processing.

    - CL, RH, SCL lapse.
    - Faculty VL converts to EL at 2 VL : 1 EL including fractional conversion.
    - EL and COL carry forward.
    """
    user_id = 999
    current_year = 2026
    next_year = 2027

    # Create balances for 2026
    LeaveBalance.objects.create(
        user_id=user_id,
        year=current_year,
        leave_category="CL",
        credited=Decimal("8.0"),
        used=Decimal("3.0"),
    )  # 5 unused -> lapse
    LeaveBalance.objects.create(
        user_id=user_id,
        year=current_year,
        leave_category="RH",
        credited=Decimal("2.0"),
        used=Decimal("1.0"),
    )  # 1 unused -> lapse
    LeaveBalance.objects.create(
        user_id=user_id,
        year=current_year,
        leave_category="SCL",
        credited=Decimal("15.0"),
        used=Decimal("5.0"),
    )  # 10 unused -> lapse
    LeaveBalance.objects.create(
        user_id=user_id,
        year=current_year,
        leave_category="VL",
        credited=Decimal("60.0"),
        used=Decimal("45.0"),
    )  # 15 unused -> convert to 7.5 EL
    LeaveBalance.objects.create(
        user_id=user_id,
        year=current_year,
        leave_category="COL",
        credited=Decimal("20.0"),
        used=Decimal("4.0"),
    )  # 16 unused -> carry forward

    # Execute year end
    stats = execute_year_end_processing(current_year=current_year)
    assert stats["converted_vl"] >= 1
    assert stats["carried_forward"] >= 1

    # Check 2027 balances
    # 1. Converted EL exists and has 7.5 days (BR-EL-007, BR-EL-008)
    el_next = LeaveBalance.objects.get(user_id=user_id, year=next_year, leave_category="EL")
    assert el_next.credited == Decimal("7.5")

    # 2. Carried forward COL exists and has 16 days (BR-EL-009)
    col_next = LeaveBalance.objects.get(user_id=user_id, year=next_year, leave_category="COL")
    assert col_next.credited == Decimal("16.0")

    # 3. VL does not carry forward as VL (BR-EL-007)
    assert not LeaveBalance.objects.filter(
        user_id=user_id, year=next_year, leave_category="VL"
    ).exists()

    # 4. CL, RH, SCL do not carry forward (BR-EL-002, BR-EL-003, BR-EL-004)
    assert not LeaveBalance.objects.filter(
        user_id=user_id, year=next_year, leave_category="CL"
    ).exists()
    assert not LeaveBalance.objects.filter(
        user_id=user_id, year=next_year, leave_category="RH"
    ).exists()
    assert not LeaveBalance.objects.filter(
        user_id=user_id, year=next_year, leave_category="SCL"
    ).exists()
