from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.policy import (
    LeaveInterval,
    LeavePolicyError,
    calculate_chargeable_days,
    convert_vl_to_el,
    intervals_overlap,
    is_category_eligible,
    require_sufficient_balance,
)


def test_vacation_leave_is_faculty_only_and_other_types_are_not_restricted():
    assert is_category_eligible("VL", "faculty")
    assert not is_category_eligible("VL", "staff")
    assert is_category_eligible("EL", "faculty")
    assert not is_category_eligible("UNKNOWN", "faculty")


def test_continuous_leave_counts_every_calendar_day():
    assert calculate_chargeable_days(
        "EL", date(2026, 10, 10), date(2026, 10, 12)
    ) == Decimal("3")


def test_half_day_cl_consumes_half_day():
    assert calculate_chargeable_days(
        "CL", date(2026, 10, 10), date(2026, 10, 10), "FIRST_HALF"
    ) == Decimal("0.5")


@pytest.mark.parametrize(
    ("code", "start", "end", "part"),
    [
        ("SCL", date(2026, 10, 10), date(2026, 10, 10), "FIRST_HALF"),
        ("CL", date(2026, 10, 10), date(2026, 10, 11), "FIRST_HALF"),
        ("EL", date(2026, 10, 10), date(2026, 10, 10), "SECOND_HALF"),
    ],
)
def test_invalid_half_day_requests_are_rejected(code, start, end, part):
    with pytest.raises(LeavePolicyError):
        calculate_chargeable_days(code, start, end, part)


def test_non_continuous_categories_require_calendar_derived_days():
    with pytest.raises(LeavePolicyError):
        calculate_chargeable_days("RH", date(2026, 10, 10), date(2026, 10, 10))
    assert calculate_chargeable_days(
        "RH", date(2026, 10, 10), date(2026, 10, 10), configured_days="1"
    ) == Decimal("1")


def test_different_cl_halves_on_same_date_do_not_overlap():
    first = LeaveInterval("CL", date(2026, 10, 10), date(2026, 10, 10), "FIRST_HALF")
    second = LeaveInterval("CL", date(2026, 10, 10), date(2026, 10, 10), "SECOND_HALF", "APPROVED")
    assert not intervals_overlap(first, second)


def test_same_half_or_full_day_cl_overlaps():
    first = LeaveInterval("CL", date(2026, 10, 10), date(2026, 10, 10), "FIRST_HALF")
    same = LeaveInterval("CL", date(2026, 10, 10), date(2026, 10, 10), "FIRST_HALF", "APPROVED")
    assert intervals_overlap(first, same)


def test_inactive_request_does_not_block_overlap():
    new = LeaveInterval("EL", date(2026, 10, 10), date(2026, 10, 12))
    rejected = LeaveInterval("CL", date(2026, 10, 11), date(2026, 10, 11), status="REJECTED")
    assert not intervals_overlap(new, rejected)


def test_balance_and_vacation_conversion_use_decimal():
    require_sufficient_balance("1.5", "1.0")
    with pytest.raises(LeavePolicyError):
        require_sufficient_balance("0.5", "1")
    assert convert_vl_to_el("1.5") == Decimal("0.75")
