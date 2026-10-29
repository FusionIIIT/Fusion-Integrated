"""Tests for modules.elm.domain.leave_policy -- pure Python, no DB.

Each test documents the BR it verifies.
"""
import datetime

import pytest

from modules.elm.domain.leave_policy import (
    CL_PER_YEAR,
    COL_PER_YEAR,
    DayHalf,
    EL_PER_YEAR,
    ExistingLeave,
    LeaveCategory,
    RH_PER_YEAR,
    SCL_PER_YEAR,
    VL_PER_YEAR,
    annual_entitlement,
    check_category_eligibility,
    convert_unused_vl_to_el,
    count_leave_days,
    has_overlap,
    is_extendable,
    is_resumable,
    requires_higher_sanction,
    requires_station_leave_info,
    validate_leave_request,
    validate_substitute,
    year_end_balances,
)
from modules.elm.domain.holidays import get_holidays


@pytest.fixture
def holidays_2026():
    return get_holidays(2026)


# -- BR-EL-001: Supported leave-category eligibility -------------------------

class TestCategoryEligibility:
    def test_valid_categories(self):
        for cat in ("CL", "RH", "SCL", "EL", "COL", "VL"):
            result = check_category_eligibility(cat, is_faculty=False)
            # EL is valid for non-faculty, VL is not
            if cat == "VL":
                assert not result.allowed
            else:
                assert result.allowed

    def test_unknown_category_rejected(self):
        result = check_category_eligibility("XYZ", is_faculty=False)
        assert not result.allowed
        assert "Unknown" in result.reason

    def test_faculty_not_eligible_for_el(self):
        """BR-EL-005: non-faculty only."""
        result = check_category_eligibility("EL", is_faculty=True)
        assert not result.allowed

    def test_non_faculty_not_eligible_for_vl(self):
        """BR-EL-006: faculty only."""
        result = check_category_eligibility("VL", is_faculty=False)
        assert not result.allowed


# -- BR-EL-002 through BR-EL-009: Entitlements -------------------------------

class TestEntitlements:
    def test_cl_entitlement(self):
        """BR-EL-002: 8 CL/year."""
        assert annual_entitlement("CL", is_faculty=False) == CL_PER_YEAR == 8

    def test_rh_entitlement(self):
        """BR-EL-003: 2 RH/year."""
        assert annual_entitlement("RH", is_faculty=False) == RH_PER_YEAR == 2

    def test_scl_entitlement(self):
        """BR-EL-004: 15 SCL/year."""
        assert annual_entitlement("SCL", is_faculty=True) == SCL_PER_YEAR == 15

    def test_el_non_faculty(self):
        """BR-EL-005: 30 EL/year for non-faculty."""
        assert annual_entitlement("EL", is_faculty=False) == EL_PER_YEAR == 30

    def test_el_faculty_zero(self):
        """BR-EL-005: faculty do not get direct EL."""
        assert annual_entitlement("EL", is_faculty=True) == 0

    def test_vl_faculty(self):
        """BR-EL-006: 60 VL/year for faculty."""
        assert annual_entitlement("VL", is_faculty=True) == VL_PER_YEAR == 60

    def test_vl_non_faculty_zero(self):
        assert annual_entitlement("VL", is_faculty=False) == 0

    def test_col_entitlement(self):
        """BR-EL-009: 20 COL/year."""
        assert annual_entitlement("COL", is_faculty=False) == COL_PER_YEAR == 20


# -- BR-EL-007, BR-EL-008: VL-to-EL conversion ------------------------------

class TestVLConversion:
    def test_conversion_ratio(self):
        """BR-EL-007: 2 VL : 1 EL."""
        assert convert_unused_vl_to_el(10) == 5.0

    def test_fractional_conversion(self):
        """BR-EL-007: fractional conversion allowed."""
        assert convert_unused_vl_to_el(7) == 3.5

    def test_zero_vl(self):
        assert convert_unused_vl_to_el(0) == 0.0


# -- BR-EL-010: Half-day CL --------------------------------------------------

class TestHalfDayCL:
    def test_first_half_consumes_half_day(self, holidays_2026):
        """BR-EL-010: approved half day consumes 0.5 CL day."""
        # A Monday that is not a holiday
        date = datetime.date(2026, 3, 2)
        days = count_leave_days(date, date, "CL", holidays_2026,
                                half=DayHalf.FIRST_HALF)
        assert days == 0.5

    def test_second_half_consumes_half_day(self, holidays_2026):
        date = datetime.date(2026, 3, 2)
        days = count_leave_days(date, date, "CL", holidays_2026,
                                half=DayHalf.SECOND_HALF)
        assert days == 0.5

    def test_full_day_cl(self, holidays_2026):
        date = datetime.date(2026, 3, 2)
        days = count_leave_days(date, date, "CL", holidays_2026,
                                half=DayHalf.FULL)
        assert days == 1.0


# -- BR-EL-011: Continuous-day counting ---------------------------------------

class TestDayCounting:
    def test_el_counts_weekends(self, holidays_2026):
        """BR-EL-011: EL counts intervening weekends."""
        # Mon 2026-05-04 to Sun 2026-05-10 = 7 calendar days
        start = datetime.date(2026, 5, 4)
        end = datetime.date(2026, 5, 10)
        days = count_leave_days(start, end, "EL", holidays_2026)
        assert days == 7.0

    def test_cl_excludes_weekends(self, holidays_2026):
        """BR-EL-011: CL excludes weekends."""
        # Mon to Sun = 5 business days
        start = datetime.date(2026, 5, 4)
        end = datetime.date(2026, 5, 10)
        days = count_leave_days(start, end, "CL", holidays_2026)
        assert days == 5.0

    def test_cl_excludes_holidays(self, holidays_2026):
        """BR-EL-011: CL excludes closed holidays."""
        # Jan 1 2026 is a holiday (Thursday)
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 1, 1)
        days = count_leave_days(start, end, "CL", holidays_2026)
        assert days == 0.0

    def test_el_counts_holidays(self, holidays_2026):
        """BR-EL-011: EL counts holidays."""
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 1, 1)
        days = count_leave_days(start, end, "EL", holidays_2026)
        assert days == 1.0

    def test_vl_counts_weekends_and_holidays(self, holidays_2026):
        """BR-EL-011: VL counts weekends and holidays like EL."""
        start = datetime.date(2026, 8, 14)  # Friday
        end = datetime.date(2026, 8, 16)    # Sunday (Aug 15 = holiday)
        days = count_leave_days(start, end, "VL", holidays_2026)
        assert days == 3.0

    def test_scl_excludes_weekends(self, holidays_2026):
        """BR-EL-011: SCL excludes weekends like CL."""
        start = datetime.date(2026, 5, 4)   # Mon
        end = datetime.date(2026, 5, 10)    # Sun
        days = count_leave_days(start, end, "SCL", holidays_2026)
        assert days == 5.0


# -- BR-EL-012: Overlap detection --------------------------------------------

class TestOverlap:
    def test_no_overlap(self):
        existing = [ExistingLeave(datetime.date(2026, 8, 1),
                                  datetime.date(2026, 8, 5), "EL")]
        assert not has_overlap(datetime.date(2026, 8, 6),
                               datetime.date(2026, 8, 10),
                               DayHalf.FULL, existing)

    def test_partial_overlap(self):
        existing = [ExistingLeave(datetime.date(2026, 8, 1),
                                  datetime.date(2026, 8, 5), "EL")]
        assert has_overlap(datetime.date(2026, 8, 4),
                           datetime.date(2026, 8, 6),
                           DayHalf.FULL, existing)

    def test_half_day_exception_different_halves(self):
        """BR-EL-012: different CL halves on same date are non-overlapping."""
        existing = [ExistingLeave(datetime.date(2026, 8, 1),
                                  datetime.date(2026, 8, 1), "CL",
                                  DayHalf.FIRST_HALF)]
        assert not has_overlap(datetime.date(2026, 8, 1),
                               datetime.date(2026, 8, 1),
                               DayHalf.SECOND_HALF, existing)

    def test_half_day_same_half_overlaps(self):
        """BR-EL-012: same CL half on same date = overlap."""
        existing = [ExistingLeave(datetime.date(2026, 8, 1),
                                  datetime.date(2026, 8, 1), "CL",
                                  DayHalf.FIRST_HALF)]
        assert has_overlap(datetime.date(2026, 8, 1),
                           datetime.date(2026, 8, 1),
                           DayHalf.FIRST_HALF, existing)


# -- BR-EL-014, BR-EL-015: Substitute validation -----------------------------

class TestSubstitute:
    def test_substitute_cannot_be_self(self):
        """BR-EL-014: substitute must not be the applicant."""
        result = validate_substitute(
            applicant_id=1, substitute_id=1,
            leave_start=datetime.date(2026, 5, 1),
            leave_end=datetime.date(2026, 5, 5),
            substitute_leaves=[])
        assert not result.allowed

    def test_substitute_with_overlap_rejected(self):
        """BR-EL-014: substitute must have no overlapping leave."""
        sub_leaves = [ExistingLeave(datetime.date(2026, 5, 3),
                                    datetime.date(2026, 5, 7), "EL")]
        result = validate_substitute(
            applicant_id=1, substitute_id=2,
            leave_start=datetime.date(2026, 5, 1),
            leave_end=datetime.date(2026, 5, 5),
            substitute_leaves=sub_leaves)
        assert not result.allowed

    def test_substitute_eligible(self):
        result = validate_substitute(
            applicant_id=1, substitute_id=2,
            leave_start=datetime.date(2026, 5, 1),
            leave_end=datetime.date(2026, 5, 5),
            substitute_leaves=[])
        assert result.allowed


# -- BR-EL-016/017: Authority routing ----------------------------------------

class TestAuthority:
    def test_cl_rh_not_higher_sanction(self):
        """BR-EL-016: CL/RH = Unit Head final."""
        assert not requires_higher_sanction("CL")
        assert not requires_higher_sanction("RH")

    def test_scl_el_col_vl_need_higher_sanction(self):
        """BR-EL-017: SCL/EL/COL/VL need higher sanction."""
        for cat in ("SCL", "EL", "COL", "VL"):
            assert requires_higher_sanction(cat)


# -- BR-EL-025: Extension applicability --------------------------------------

class TestExtension:
    def test_el_col_vl_extendable(self):
        """BR-EL-025: only EL/COL/VL may be extended."""
        for cat in ("EL", "COL", "VL"):
            assert is_extendable(cat)

    def test_cl_rh_scl_not_extendable(self):
        for cat in ("CL", "RH", "SCL"):
            assert not is_extendable(cat)


# -- BR-EL-027: Resumption ---------------------------------------------------

class TestResumption:
    def test_el_col_vl_resumable(self):
        """BR-EL-027: formal resumption for EL/COL/VL."""
        for cat in ("EL", "COL", "VL"):
            assert is_resumable(cat)

    def test_cl_rh_scl_not_resumable(self):
        for cat in ("CL", "RH", "SCL"):
            assert not is_resumable(cat)


# -- BR-EL-013: Station leave ------------------------------------------------

class TestStationLeave:
    def test_el_col_vl_require_station_info(self):
        """BR-EL-013: station leave captured within application."""
        for cat in ("EL", "COL", "VL"):
            assert requires_station_leave_info(cat)

    def test_cl_rh_scl_no_station_info(self):
        for cat in ("CL", "RH", "SCL"):
            assert not requires_station_leave_info(cat)


# -- Year-end processing (BR-EL-002 through BR-EL-009) -----------------------

class TestYearEnd:
    def test_non_faculty_year_end(self):
        """BR-EL-002/005/009: CL/RH/SCL lapse; EL/COL carry forward."""
        balances = {"CL": 5.0, "RH": 1.0, "SCL": 10.0,
                    "EL": 20.0, "COL": 15.0, "VL": 0.0}
        new = year_end_balances(balances, is_faculty=False)

        assert new["CL"] == 8.0   # reset to annual
        assert new["RH"] == 2.0   # reset to annual
        assert new["SCL"] == 15.0  # reset to annual
        assert new["EL"] == 20.0 + 30.0  # carry + new credit
        assert new["COL"] == 15.0 + 20.0  # carry + new credit
        assert new["VL"] == 0.0   # non-faculty

    def test_faculty_year_end_with_vl_conversion(self):
        """BR-EL-007/008: unused VL converts to EL at 2:1."""
        balances = {"CL": 3.0, "RH": 0.0, "SCL": 5.0,
                    "EL": 10.0, "COL": 5.0, "VL": 20.0}
        new = year_end_balances(balances, is_faculty=True)

        assert new["CL"] == 8.0
        assert new["RH"] == 2.0
        assert new["SCL"] == 15.0
        # EL = old(10) + VL_conversion(20/2=10) = 20
        assert new["EL"] == 20.0
        # VL resets (no carry-forward)
        assert new["VL"] == 60.0
        assert new["COL"] == 5.0 + 20.0

    def test_fractional_vl_conversion(self):
        """BR-EL-007: fractional conversion allowed."""
        balances = {"CL": 0.0, "RH": 0.0, "SCL": 0.0,
                    "EL": 0.0, "COL": 0.0, "VL": 7.0}
        new = year_end_balances(balances, is_faculty=True)
        assert new["EL"] == 3.5


# -- Full validate_leave_request integration ----------------------------------

class TestValidateLeaveRequest:
    def test_valid_cl_request(self, holidays_2026):
        result = validate_leave_request(
            category="CL",
            start=datetime.date(2026, 3, 2),
            end=datetime.date(2026, 3, 3),
            is_faculty=False,
            balance=8.0,
            existing_leaves=[],
            holidays=holidays_2026)
        assert result.allowed
        assert result.days_counted == 2.0

    def test_insufficient_balance_rejected(self, holidays_2026):
        result = validate_leave_request(
            category="CL",
            start=datetime.date(2026, 3, 2),
            end=datetime.date(2026, 3, 13),
            is_faculty=False,
            balance=1.0,
            existing_leaves=[],
            holidays=holidays_2026)
        assert not result.allowed
        assert "Insufficient" in result.reason

    def test_overlap_rejected(self, holidays_2026):
        existing = [ExistingLeave(datetime.date(2026, 8, 1),
                                  datetime.date(2026, 8, 5), "EL")]
        result = validate_leave_request(
            category="CL",
            start=datetime.date(2026, 8, 4),
            end=datetime.date(2026, 8, 6),
            is_faculty=False,
            balance=8.0,
            existing_leaves=existing,
            holidays=holidays_2026)
        assert not result.allowed
        assert "overlap" in result.reason.lower()

    def test_end_before_start_rejected(self, holidays_2026):
        result = validate_leave_request(
            category="CL",
            start=datetime.date(2026, 3, 5),
            end=datetime.date(2026, 3, 2),
            is_faculty=False,
            balance=8.0,
            existing_leaves=[],
            holidays=holidays_2026)
        assert not result.allowed

    def test_faculty_el_rejected(self, holidays_2026):
        result = validate_leave_request(
            category="EL",
            start=datetime.date(2026, 5, 1),
            end=datetime.date(2026, 5, 5),
            is_faculty=True,
            balance=30.0,
            existing_leaves=[],
            holidays=holidays_2026)
        assert not result.allowed

    def test_non_faculty_vl_rejected(self, holidays_2026):
        result = validate_leave_request(
            category="VL",
            start=datetime.date(2026, 6, 1),
            end=datetime.date(2026, 6, 5),
            is_faculty=False,
            balance=60.0,
            existing_leaves=[],
            holidays=holidays_2026)
        assert not result.allowed

    def test_half_day_cl_with_balance(self, holidays_2026):
        """BR-EL-010: half-day CL = 0.5 days."""
        result = validate_leave_request(
            category="CL",
            start=datetime.date(2026, 3, 2),
            end=datetime.date(2026, 3, 2),
            is_faculty=False,
            balance=0.5,
            existing_leaves=[],
            holidays=holidays_2026,
            half=DayHalf.FIRST_HALF)
        assert result.allowed
        assert result.days_counted == 0.5
