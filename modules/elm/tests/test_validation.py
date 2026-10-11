from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from modules.elm.services.validation import (
    calculate_leave_days,
    cl_halves_are_compatible,
    date_intervals_overlap,
    iter_dates,
    validate_date_range,
)


def test_continuous_leave_counts_both_endpoints():
    assert calculate_leave_days(
        "EL", date(2026, 10, 10), date(2026, 10, 12)
    ) == Decimal("3")


def test_half_day_cl_consumes_half_day():
    assert calculate_leave_days(
        "CL", date(2026, 10, 10), date(2026, 10, 10), "first"
    ) == Decimal("0.5")


def test_half_day_is_not_allowed_for_el():
    with pytest.raises(ValidationError):
        calculate_leave_days(
            "EL", date(2026, 10, 10), date(2026, 10, 10), "first"
        )


def test_end_before_start_is_rejected():
    with pytest.raises(ValidationError):
        validate_date_range(date(2026, 10, 12), date(2026, 10, 10))


def test_different_cl_halves_do_not_conflict():
    d = date(2026, 10, 10)
    assert cl_halves_are_compatible(
        "CL", d, d, "first", "CL", d, d, "second"
    )


def test_same_cl_half_is_not_compatible():
    d = date(2026, 10, 10)
    assert not cl_halves_are_compatible(
        "CL", d, d, "first", "CL", d, d, "first"
    )


def test_date_intervals_overlap_inclusively():
    assert date_intervals_overlap(
        date(2026, 10, 10), date(2026, 10, 12),
        date(2026, 10, 12), date(2026, 10, 15),
    )


def test_non_overlapping_intervals():
    assert not date_intervals_overlap(
        date(2026, 10, 10), date(2026, 10, 12),
        date(2026, 10, 13), date(2026, 10, 15),
    )


def test_iter_dates_is_inclusive():
    assert list(iter_dates(date(2026, 10, 10), date(2026, 10, 12))) == [
        date(2026, 10, 10),
        date(2026, 10, 11),
        date(2026, 10, 12),
    ]
