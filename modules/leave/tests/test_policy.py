from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain import policy

FRI = date(2026, 11, 6)  # a Friday
MON = date(2026, 11, 9)  # the following Monday


def test_entitlement_cl_staff():
    """CL for staff is Decimal("8") (BR-EL-002)."""
    assert policy.entitlement("CL", "staff") == Decimal("8")


def test_entitlement_el_faculty_none():
    """EL for faculty is None (BR-EL-005)."""
    assert policy.entitlement("EL", "faculty") is None


def test_entitlement_vl_staff_none():
    """VL for staff is None (BR-EL-006)."""
    assert policy.entitlement("VL", "staff") is None


def test_entitlement_vl_faculty():
    """VL for faculty is Decimal("60")."""
    assert policy.entitlement("VL", "faculty") == Decimal("60")


def test_entitlement_any_kind_as_staff():
    """Any kind other than 'faculty' (e.g., 'employee') is treated as staff. EL gives Decimal("30")."""
    assert policy.entitlement("EL", "employee") == Decimal("30")
    assert policy.entitlement("EL", "") == Decimal("30")


def test_count_days_cl_fri_mon():
    """CL from FRI to MON is Decimal("2") because weekends are not counted (BR-EL-011)."""
    assert policy.count_days("CL", FRI, MON) == Decimal("2")


def test_count_days_el_fri_mon():
    """EL from FRI to MON is Decimal("4") because EL counts calendar days (BR-EL-011)."""
    assert policy.count_days("EL", FRI, MON) == Decimal("4")


def test_count_days_cl_mon_half_day_first():
    """CL on MON alone with half_day 'first' is Decimal("0.5") (BR-EL-010)."""
    assert policy.count_days("CL", MON, MON, "first") == Decimal("0.5")


def test_count_days_el_mon_half_day_first_raises():
    """half_day 'first' on EL raises policy.PolicyError."""
    with pytest.raises(policy.PolicyError):
        policy.count_days("EL", MON, MON, "first")


def test_count_days_cl_two_day_half_day_first_raises():
    """half_day 'first' on a two-day CL raises policy.PolicyError."""
    with pytest.raises(policy.PolicyError):
        policy.count_days("CL", FRI, MON, "first")


def test_count_days_end_before_start_raises():
    """end before start raises policy.PolicyError."""
    with pytest.raises(policy.PolicyError):
        policy.count_days("CL", MON, FRI)


def test_overlaps_no_overlap_different_days():
    """FRI..FRI and MON..MON with no half days do not overlap (BR-EL-012)."""
    assert not policy.overlaps(FRI, FRI, "none", MON, MON, "none")


def test_overlaps_overlap_shared_day():
    """FRI..MON and MON..MON overlap (BR-EL-012)."""
    assert policy.overlaps(FRI, MON, "none", MON, MON, "none")


def test_overlaps_no_overlap_different_halves_same_day():
    """MON first half and MON second half do not overlap (BR-EL-012)."""
    assert not policy.overlaps(MON, MON, "first", MON, MON, "second")


def test_overlaps_overlap_same_half_same_day():
    """MON first half and MON first half overlap (BR-EL-012)."""
    assert policy.overlaps(MON, MON, "first", MON, MON, "first")


def test_unit_head_is_final_cl():
    """unit_head_is_final is True for 'CL' (BR-EL-016)."""
    assert policy.unit_head_is_final("CL") is True


def test_unit_head_is_final_rh():
    """unit_head_is_final is True for 'RH' (BR-EL-016)."""
    assert policy.unit_head_is_final("RH") is True


def test_unit_head_is_final_el_false():
    """unit_head_is_final is False for 'EL' (BR-EL-017)."""
    assert policy.unit_head_is_final("EL") is False
