from decimal import Decimal

from modules.leave.domain.entitlement import (
    calculate_vl_to_el_conversion,
    get_annual_quota,
)


def test_annual_quotas_by_cadre():
    # Faculty quotas
    assert get_annual_quota("faculty", "CL") == Decimal("8.0")
    assert get_annual_quota("faculty", "RH") == Decimal("2.0")
    assert get_annual_quota("faculty", "SCL") == Decimal("15.0")
    assert get_annual_quota("faculty", "EL") == Decimal("0.0")
    assert get_annual_quota("faculty", "COL") == Decimal("20.0")
    assert get_annual_quota("faculty", "VL") == Decimal("60.0")

    # Staff quotas
    assert get_annual_quota("staff", "CL") == Decimal("8.0")
    assert get_annual_quota("staff", "RH") == Decimal("2.0")
    assert get_annual_quota("staff", "SCL") == Decimal("15.0")
    assert get_annual_quota("staff", "EL") == Decimal("30.0")
    assert get_annual_quota("staff", "COL") == Decimal("20.0")
    assert get_annual_quota("staff", "VL") == Decimal("0.0")


def test_vl_to_el_year_end_conversion_br_el_007():
    # 2 VL : 1 EL conversion including fractional values
    assert calculate_vl_to_el_conversion(Decimal("60.0")) == Decimal("30.0")
    assert calculate_vl_to_el_conversion(Decimal("15.0")) == Decimal("7.5")
    assert calculate_vl_to_el_conversion(Decimal("1.0")) == Decimal("0.5")
    assert calculate_vl_to_el_conversion(Decimal("0.0")) == Decimal("0.0")
