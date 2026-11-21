from decimal import Decimal

import pytest

from modules.elm.domain.leave_rules import LeaveRuleError
from modules.elm.models import LeaveBalance, LeaveType, YearEndConversion
from modules.elm.services.year_end import convert_vl_to_el


@pytest.mark.django_db
def test_year_end_conversion_credits_el_and_clears_vl():
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=LeaveType.VL,
        leave_year=2026,
        entitlement=Decimal("60"),
        available_balance=Decimal("5.5"),
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=LeaveType.EL,
        leave_year=2027,
        entitlement=Decimal("30"),
        available_balance=Decimal("4"),
    )

    result = convert_vl_to_el(user_id=101, source_year=2026)

    vl = LeaveBalance.objects.get(user_id=101, leave_type=LeaveType.VL, leave_year=2026)
    el = LeaveBalance.objects.get(user_id=101, leave_type=LeaveType.EL, leave_year=2027)

    assert result.unused_vl == Decimal("5.5")
    assert result.converted_el == Decimal("2.75")
    assert vl.available_balance == Decimal("0")
    assert el.available_balance == Decimal("6.75")


@pytest.mark.django_db
def test_year_end_conversion_cannot_be_applied_twice():
    LeaveBalance.objects.create(
        user_id=102,
        leave_type=LeaveType.VL,
        leave_year=2026,
        entitlement=Decimal("60"),
        available_balance=Decimal("5"),
    )

    convert_vl_to_el(user_id=102, source_year=2026)

    with pytest.raises(LeaveRuleError, match="already been recorded"):
        convert_vl_to_el(user_id=102, source_year=2026)

    el = LeaveBalance.objects.get(user_id=102, leave_type=LeaveType.EL, leave_year=2027)
    assert el.available_balance == Decimal("2.5")
    assert YearEndConversion.objects.filter(user_id=102, source_year=2026).count() == 1


@pytest.mark.django_db
def test_year_end_conversion_rejects_missing_vl_balance():
    with pytest.raises(LeaveRuleError, match="No VL balance exists"):
        convert_vl_to_el(user_id=103, source_year=2026)


@pytest.mark.django_db
def test_zero_unused_vl_records_zero_conversion():
    LeaveBalance.objects.create(
        user_id=104,
        leave_type=LeaveType.VL,
        leave_year=2026,
        entitlement=Decimal("60"),
        available_balance=Decimal("0"),
    )

    result = convert_vl_to_el(user_id=104, source_year=2026)

    assert result.converted_el == Decimal("0")
    assert LeaveBalance.objects.get(
        user_id=104, leave_type=LeaveType.VL, leave_year=2026
    ).available_balance == Decimal("0")
