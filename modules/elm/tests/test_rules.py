"""Unit tests for ELM pure Python domain rules."""
from datetime import date

import pytest

from modules.elm.domain.rules import (
    calculate_leave_days,
    is_date_overlap,
    validate_substitute,
)


class TestCalculateLeaveDays:
    def test_continuous_count_leaves_include_weekends(self):
        """EL, COL, and VL count all calendar days continuously (BR-EL-011)."""
        # Friday 2026-10-02 to Monday 2026-10-05 = 4 calendar days (Fri, Sat, Sun, Mon)
        start = date(2026, 10, 2)
        end = date(2026, 10, 5)

        for ltype in ["EL", "COL", "VL"]:
            assert calculate_leave_days(ltype, start, end) == 4.0

    def test_working_day_leaves_exclude_weekends(self):
        """CL, SCL, and RH exclude weekends from count (BR-EL-011)."""
        # Friday 2026-10-02 to Monday 2026-10-05 = 2 working days (Fri, Mon)
        start = date(2026, 10, 2)
        end = date(2026, 10, 5)

        for ltype in ["CL", "SCL", "RH"]:
            assert calculate_leave_days(ltype, start, end) == 2.0

    def test_half_day_casual_leave(self):
        """Half-day leave consumes 0.5 days for CL on a single date (BR-EL-010)."""
        d = date(2026, 10, 2)
        assert calculate_leave_days("CL", d, d, half_day=True) == 0.5

    def test_half_day_non_cl_raises_value_error(self):
        """Half-day leave on non-CL categories is invalid (BR-EL-010)."""
        d = date(2026, 10, 2)
        for ltype in ["RH", "SCL", "EL", "COL", "VL"]:
            with pytest.raises(ValueError, match="Half-day leave is only permitted for Casual Leave"):
                calculate_leave_days(ltype, d, d, half_day=True)

    def test_half_day_multi_date_raises_value_error(self):
        """Half-day leave cannot span multiple dates."""
        start = date(2026, 10, 2)
        end = date(2026, 10, 3)
        with pytest.raises(ValueError, match="Half-day leave must be for a single date"):
            calculate_leave_days("CL", start, end, half_day=True)

    def test_start_after_end_raises_value_error(self):
        """Start date after end date is rejected."""
        start = date(2026, 10, 5)
        end = date(2026, 10, 2)
        with pytest.raises(ValueError, match="start_date cannot be after end_date"):
            calculate_leave_days("CL", start, end)


class TestValidateSubstitute:
    def test_applicant_cannot_be_own_substitute(self):
        """Applicant cannot nominate themselves (BR-EL-014)."""
        with pytest.raises(ValueError, match="Applicant cannot nominate themselves"):
            validate_substitute(applicant_id=101, substitute_id=101)

    def test_valid_substitute_passes(self):
        """Distinct substitute ID passes."""
        validate_substitute(applicant_id=101, substitute_id=102)

    def test_none_substitute_passes(self):
        """None substitute ID passes."""
        validate_substitute(applicant_id=101, substitute_id=None)


class TestIsDateOverlap:
    def test_disjoint_dates_do_not_overlap(self):
        """Non-overlapping dates return False."""
        assert not is_date_overlap(
            date(2026, 10, 1), date(2026, 10, 3),
            date(2026, 10, 5), date(2026, 10, 7),
        )

    def test_overlapping_full_dates(self):
        """Overlapping date intervals return True."""
        assert is_date_overlap(
            date(2026, 10, 1), date(2026, 10, 5),
            date(2026, 10, 4), date(2026, 10, 8),
        )

    def test_half_day_cl_exception_on_same_date(self):
        """First-half and second-half CL on the same date do NOT overlap (BR-EL-012)."""
        d = date(2026, 10, 5)
        overlap = is_date_overlap(
            start1=d, end1=d, start2=d, end2=d,
            half_day1=True, half_type1="first_half",
            half_day2=True, half_type2="second_half",
        )
        assert not overlap

    def test_half_day_cl_same_half_overlaps(self):
        """Two first-half requests on the same date DO overlap."""
        d = date(2026, 10, 5)
        overlap = is_date_overlap(
            start1=d, end1=d, start2=d, end2=d,
            half_day1=True, half_type1="first_half",
            half_day2=True, half_type2="first_half",
        )
        assert overlap
