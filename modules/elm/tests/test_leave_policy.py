from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave_policy import LeaveCategory, LeavePolicy


def test_leave_category_enum():
    assert LeaveCategory.CL == "CL"
    assert LeaveCategory.RH == "RH"
    assert LeaveCategory.SCL == "SCL"
    assert LeaveCategory.EL == "EL"
    assert LeaveCategory.COL == "COL"
    assert LeaveCategory.VL == "VL"

def test_leave_policy_initialization():
    policy = LeavePolicy(LeaveCategory.CL, Decimal("8"))
    assert policy.category == LeaveCategory.CL
    assert policy.annual_entitlement == Decimal("8")

def test_validate_date_interval():
    policy = LeavePolicy(LeaveCategory.CL, Decimal("8"))
    with pytest.raises(ValueError):
        policy.validate_date_interval(date(2023, 12, 31), date(2023, 12, 30))

def test_validate_numeric_input():
    policy = LeavePolicy(LeaveCategory.CL, Decimal("8"))
    with pytest.raises(ValueError):
        policy.validate_numeric_input("invalid")

def test_calculate_days_cl():
    policy = LeavePolicy(LeaveCategory.CL, Decimal("8"))
    with pytest.raises(ValueError):
        policy.calculate_days(date(2023, 1, 1), date(2023, 1, 2))
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 1)) == Decimal("1")

def test_calculate_days_rh():
    policy = LeavePolicy(LeaveCategory.RH, Decimal("2"))
    with pytest.raises(ValueError):
        policy.calculate_days(date(2023, 1, 1), date(2023, 1, 2))
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 1)) == Decimal("1")

def test_calculate_days_scl():
    policy = LeavePolicy(LeaveCategory.SCL, Decimal("15"))
    with pytest.raises(ValueError):
        policy.calculate_days(date(2023, 1, 1), date(2023, 1, 2))
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 1)) == Decimal("1")

def test_calculate_days_el():
    policy = LeavePolicy(LeaveCategory.EL, Decimal("30"))
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 2)) == Decimal("2")
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 1)) == Decimal("1")

def test_calculate_days_col():
    policy = LeavePolicy(LeaveCategory.COL, Decimal("20"))
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 2)) == Decimal("2")
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 1)) == Decimal("1")

def test_calculate_days_vl():
    policy = LeavePolicy(LeaveCategory.VL, Decimal("60"))
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 2)) == Decimal("2")
    assert policy.calculate_days(date(2023, 1, 1), date(2023, 1, 1)) == Decimal("1")

def test_year_end_treatment_cl():
    policy = LeavePolicy(LeaveCategory.CL, Decimal("8"))
    assert policy.year_end_treatment(Decimal("5")) == Decimal("0")

def test_year_end_treatment_rh():
    policy = LeavePolicy(LeaveCategory.RH, Decimal("2"))
    assert policy.year_end_treatment(Decimal("1")) == Decimal("0")

def test_year_end_treatment_scl():
    policy = LeavePolicy(LeaveCategory.SCL, Decimal("15"))
    assert policy.year_end_treatment(Decimal("10")) == Decimal("0")

def test_year_end_treatment_el():
    policy = LeavePolicy(LeaveCategory.EL, Decimal("30"))
    assert policy.year_end_treatment(Decimal("25")) == Decimal("25")

def test_year_end_treatment_col():
    policy = LeavePolicy(LeaveCategory.COL, Decimal("20"))
    assert policy.year_end_treatment(Decimal("15")) == Decimal("15")

def test_year_end_treatment_vl():
    policy = LeavePolicy(LeaveCategory.VL, Decimal("60"))
    assert policy.year_end_treatment(Decimal("30")) == Decimal("15")
