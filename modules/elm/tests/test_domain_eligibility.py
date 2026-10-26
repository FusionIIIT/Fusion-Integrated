"""Domain tests for ELM eligibility and validation rules.

Pure Python, no database.
Verifies BR-EL-001, BR-EL-003, BR-EL-006, BR-EL-012, BR-EL-013, BR-EL-014.
"""
import datetime
import unittest

from modules.elm.domain.constants import HalfDayPeriod, LeaveCategory
from modules.elm.domain.eligibility import (
    ExistingLeaveSpan,
    VacationPeriod,
    check_applicant_overlap,
    check_category_eligibility,
    check_rh_calendar_applicability,
    check_station_leave_coupling,
    check_substitute_eligibility,
    check_vl_vacation_applicability,
)


class TestLeaveEligibility(unittest.TestCase):

    def test_category_eligibility_faculty_vs_staff(self):
        """BR-EL-001 / BR-EL-006: VL is faculty only."""
        # Faculty can access VL
        res = check_category_eligibility(LeaveCategory.VL, is_faculty=True)
        self.assertTrue(res.is_valid)

        # Non-faculty cannot access VL
        res_non_fac = check_category_eligibility(LeaveCategory.VL, is_faculty=False)
        self.assertFalse(res_non_fac.is_valid)
        self.assertEqual(res_non_fac.error_code, "vl_faculty_only")

        # Both can access CL, EL, COL, RH, SCL
        self.assertTrue(check_category_eligibility(LeaveCategory.CL, is_faculty=False).is_valid)
        self.assertTrue(check_category_eligibility(LeaveCategory.EL, is_faculty=False).is_valid)

    def test_rh_calendar_applicability(self):
        """BR-EL-003 / BR-EL-031: RH request must match published RH date."""
        published_rh = {datetime.date(2026, 11, 4), datetime.date(2026, 11, 15)}

        # Matching date passes
        res_valid = check_rh_calendar_applicability(datetime.date(2026, 11, 4), published_rh)
        self.assertTrue(res_valid.is_valid)

        # Non-matching date is blocked
        res_invalid = check_rh_calendar_applicability(datetime.date(2026, 11, 5), published_rh)
        self.assertFalse(res_invalid.is_valid)
        self.assertEqual(res_invalid.error_code, "rh_not_on_calendar")

    def test_vl_vacation_period_applicability(self):
        """BR-EL-006: VL must fall entirely within an Academic Calendar vacation period."""
        vacation = [
            VacationPeriod(
                name="Summer Vacation",
                start_date=datetime.date(2026, 5, 1),
                end_date=datetime.date(2026, 6, 30),
            )
        ]

        # Inside vacation period -> Valid
        res_in = check_vl_vacation_applicability(
            datetime.date(2026, 5, 10), datetime.date(2026, 5, 20), vacation
        )
        self.assertTrue(res_in.is_valid)

        # Spilling outside vacation period -> Invalid
        res_out = check_vl_vacation_applicability(
            datetime.date(2026, 6, 25), datetime.date(2026, 7, 5), vacation
        )
        self.assertFalse(res_out.is_valid)
        self.assertEqual(res_out.error_code, "vl_outside_vacation_period")

    def test_applicant_overlap_detection(self):
        """BR-EL-012: Detect and block impermissible leave overlap."""
        existing = [
            ExistingLeaveSpan(
                leave_id=101,
                category=LeaveCategory.EL,
                start_date=datetime.date(2026, 10, 10),
                end_date=datetime.date(2026, 10, 15),
            )
        ]

        # Overlapping span
        res_overlap = check_applicant_overlap(
            category=LeaveCategory.CL,
            start_date=datetime.date(2026, 10, 12),
            end_date=datetime.date(2026, 10, 14),
            is_half_day=False,
            half_day_period="NONE",
            existing_leaves=existing,
        )
        self.assertFalse(res_overlap.is_valid)
        self.assertEqual(res_overlap.error_code, "overlapping_leave")

        # Non-overlapping span
        res_clean = check_applicant_overlap(
            category=LeaveCategory.CL,
            start_date=datetime.date(2026, 10, 16),
            end_date=datetime.date(2026, 10, 18),
            is_half_day=False,
            half_day_period="NONE",
            existing_leaves=existing,
        )
        self.assertTrue(res_clean.is_valid)

    def test_half_day_cl_overlap_exception(self):
        """BR-EL-012: First-half and second-half CL on the same date are NOT treated as overlapping!"""
        target_date = datetime.date(2026, 10, 20)
        existing = [
            ExistingLeaveSpan(
                leave_id=201,
                category=LeaveCategory.CL,
                start_date=target_date,
                end_date=target_date,
                is_half_day=True,
                half_day_period=HalfDayPeriod.FIRST_HALF,
            )
        ]

        # Second-half CL on the same date: PERMITTED by BR-EL-012!
        res_second = check_applicant_overlap(
            category=LeaveCategory.CL,
            start_date=target_date,
            end_date=target_date,
            is_half_day=True,
            half_day_period=HalfDayPeriod.SECOND_HALF,
            existing_leaves=existing,
        )
        self.assertTrue(res_second.is_valid)

        # Another FIRST_HALF on the same date: OVERLAPPING and BLOCKED!
        res_first_dup = check_applicant_overlap(
            category=LeaveCategory.CL,
            start_date=target_date,
            end_date=target_date,
            is_half_day=True,
            half_day_period=HalfDayPeriod.FIRST_HALF,
            existing_leaves=existing,
        )
        self.assertFalse(res_first_dup.is_valid)

        # Full day CL on the same date: OVERLAPPING and BLOCKED!
        res_full = check_applicant_overlap(
            category=LeaveCategory.CL,
            start_date=target_date,
            end_date=target_date,
            is_half_day=False,
            half_day_period="NONE",
            existing_leaves=existing,
        )
        self.assertFalse(res_full.is_valid)

    def test_substitute_eligibility(self):
        """BR-EL-014: Substitute must be another employee, not self, no conflicting active leave."""
        start = datetime.date(2026, 11, 1)
        end = datetime.date(2026, 11, 5)

        # Self-nomination is blocked
        res_self = check_substitute_eligibility(
            applicant_id=1,
            substitute_id=1,
            start_date=start,
            end_date=end,
            substitute_active_leaves=[],
        )
        self.assertFalse(res_self.is_valid)
        self.assertEqual(res_self.error_code, "substitute_self_nomination")

        # Substitute with overlapping leave is blocked
        sub_conflicts = [
            ExistingLeaveSpan(
                leave_id=301,
                category=LeaveCategory.CL,
                start_date=datetime.date(2026, 11, 3),
                end_date=datetime.date(2026, 11, 4),
            )
        ]
        res_conflict = check_substitute_eligibility(
            applicant_id=1,
            substitute_id=2,
            start_date=start,
            end_date=end,
            substitute_active_leaves=sub_conflicts,
        )
        self.assertFalse(res_conflict.is_valid)
        self.assertEqual(res_conflict.error_code, "substitute_has_overlapping_leave")

        # Eligible substitute passes
        res_ok = check_substitute_eligibility(
            applicant_id=1,
            substitute_id=2,
            start_date=start,
            end_date=end,
            substitute_active_leaves=[],
        )
        self.assertTrue(res_ok.is_valid)

    def test_station_leave_coupling(self):
        """BR-EL-013: Validate station leave fields."""
        d1 = datetime.date(2026, 11, 1)
        d2 = datetime.date(2026, 11, 5)

        # Valid station leave
        res_valid = check_station_leave_coupling(
            is_station_leave=True,
            leave_start=d1,
            leave_end=d2,
            station_start=d1,
            station_end=d2,
            station_destination="New Delhi",
        )
        self.assertTrue(res_valid.is_valid)

        # Missing destination
        res_no_dest = check_station_leave_coupling(
            is_station_leave=True,
            leave_start=d1,
            leave_end=d2,
            station_start=d1,
            station_end=d2,
            station_destination="",
        )
        self.assertFalse(res_no_dest.is_valid)


if __name__ == "__main__":
    unittest.main()
