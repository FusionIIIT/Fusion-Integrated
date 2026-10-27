"""Unit tests for ELM business rules and domain logic."""
import unittest
from datetime import date

from modules.elm.domain.calculations import (
    calculate_leave_days,
    calculate_vl_to_el_conversion,
)
from modules.elm.domain.validation import (
    ValidationError,
    validate_category_eligibility,
    validate_restricted_holiday,
    validate_vacation_period,
    validate_no_overlap,
    validate_substitute,
)
from modules.elm.domain.state_machine import (
    determine_initial_status,
    process_substitute_action,
    process_unit_head_action,
    process_sanction_action,
    can_withdraw,
    can_request_cancellation,
)


class TestELMCalculations(unittest.TestCase):
    def test_continuous_counting_for_el_col_vl(self):
        """BR-EL-011: EL, COL, VL count continuously across weekends and holidays."""
        # Friday to Monday = 4 days
        start = date(2026, 11, 6)   # Friday
        end = date(2026, 11, 9)     # Monday
        for cat in ("EL", "COL", "VL"):
            days = calculate_leave_days(cat, start, end)
            self.assertEqual(days, 4.0, f"Expected 4 days continuous count for {cat}")

    def test_working_day_counting_for_cl_rh_scl(self):
        """BR-EL-011: CL, RH, SCL exclude weekends and closed holidays."""
        # Friday to Monday: Friday (1) + Sat (0) + Sun (0) + Mon (holiday, 0) = 1 day
        start = date(2026, 11, 6)   # Friday
        end = date(2026, 11, 9)     # Monday
        closed_holidays = {date(2026, 11, 9)}
        days = calculate_leave_days("CL", start, end, closed_holidays=closed_holidays)
        self.assertEqual(days, 1.0)

    def test_half_day_cl_treatment(self):
        """BR-EL-010: Half-day CL consumes 0.5 days on a single date."""
        today = date(2026, 11, 10)
        days = calculate_leave_days("CL", today, today, half_day="first_half")
        self.assertEqual(days, 0.5)

        days_second = calculate_leave_days("CL", today, today, half_day="second_half")
        self.assertEqual(days_second, 0.5)

        # Multi-day half-day CL should raise ValueError
        with self.assertRaises(ValueError):
            calculate_leave_days("CL", date(2026, 11, 10), date(2026, 11, 11), half_day="first_half")

    def test_vl_to_el_conversion(self):
        """BR-EL-007: Unused VL converts to EL at 2 VL : 1 EL including fractions."""
        self.assertEqual(calculate_vl_to_el_conversion(60), 30.0)
        self.assertEqual(calculate_vl_to_el_conversion(25), 12.5)
        self.assertEqual(calculate_vl_to_el_conversion(0), 0.0)


class TestELMValidation(unittest.TestCase):
    def test_category_eligibility(self):
        """BR-EL-001, BR-EL-006: Only faculty can avail Vacation Leave."""
        validate_category_eligibility("VL", "faculty")
        with self.assertRaises(ValidationError):
            validate_category_eligibility("VL", "staff")

    def test_restricted_holiday_validation(self):
        """BR-EL-003: RH must be on a published RH calendar date."""
        published = {date(2026, 11, 12)}
        validate_restricted_holiday("RH", date(2026, 11, 12), date(2026, 11, 12), published)

        with self.assertRaises(ValidationError):
            validate_restricted_holiday("RH", date(2026, 11, 13), date(2026, 11, 13), published)

    def test_vacation_period_validation(self):
        """BR-EL-006: VL must be within an active vacation period."""
        vacations = [(date(2026, 6, 1), date(2026, 7, 15))]
        validate_vacation_period("VL", date(2026, 6, 10), date(2026, 6, 20), vacations)

        with self.assertRaises(ValidationError):
            validate_vacation_period("VL", date(2026, 7, 10), date(2026, 7, 20), vacations)

    def test_overlap_and_half_day_exception(self):
        """BR-EL-012: No overlap allowed except first-half and second-half CL on same date."""
        target_day = date(2026, 11, 10)
        existing = [(target_day, target_day, "first_half")]

        # Second half on the same date should pass
        validate_no_overlap(target_day, target_day, "second_half", existing)

        # Full day or same half on the same date should fail
        with self.assertRaises(ValidationError):
            validate_no_overlap(target_day, target_day, "none", existing)

        with self.assertRaises(ValidationError):
            validate_no_overlap(target_day, target_day, "first_half", existing)

    def test_substitute_validation(self):
        """BR-EL-014: Cannot nominate self or substitute with active leaves."""
        with self.assertRaises(ValidationError):
            validate_substitute(1, 1, date(2026, 11, 10), date(2026, 11, 12), [])

        sub_leaves = [(date(2026, 11, 10), date(2026, 11, 15))]
        with self.assertRaises(ValidationError):
            validate_substitute(1, 2, date(2026, 11, 12), date(2026, 11, 14), sub_leaves)


class TestELMStateMachine(unittest.TestCase):
    def test_initial_routing(self):
        """BR-EL-015: Substitute gate precedes Unit Head review."""
        self.assertEqual(determine_initial_status(has_substitute=True), "pending_substitute")
        self.assertEqual(determine_initial_status(has_substitute=False), "pending_unit_head")

    def test_substitute_consent_progression(self):
        sub_status, wf_status = process_substitute_action("accept")
        self.assertEqual(sub_status, "accepted")
        self.assertEqual(wf_status, "pending_unit_head")

        sub_status, wf_status = process_substitute_action("decline")
        self.assertEqual(sub_status, "declined")
        self.assertEqual(wf_status, "pending_substitute")

    def test_unit_head_final_for_cl_rh(self):
        """BR-EL-016: Unit head is final for CL and RH."""
        rec, status = process_unit_head_action("CL", "approve")
        self.assertEqual(status, "approved")

        rec, status = process_unit_head_action("RH", "reject")
        self.assertEqual(status, "rejected")

    def test_unit_head_recommendation_for_higher_sanction(self):
        """BR-EL-017: Unit Head records recommended/not recommended for SCL, EL, COL, VL."""
        for cat in ("SCL", "EL", "COL", "VL"):
            rec, status = process_unit_head_action(cat, "recommend")
            self.assertEqual(rec, "recommended")
            self.assertEqual(status, "pending_sanction")

            rec, status = process_unit_head_action(cat, "not_recommend")
            self.assertEqual(rec, "not_recommended")
            self.assertEqual(status, "pending_sanction")

    def test_withdrawal_and_cancellation_rules(self):
        """BR-EL-022, BR-EL-023: Immediate withdrawal while pending; cancellation only before start."""
        self.assertTrue(can_withdraw("pending_unit_head"))
        self.assertTrue(can_withdraw("pending_sanction"))
        self.assertFalse(can_withdraw("approved"))
        self.assertFalse(can_withdraw("rejected"))

        today = date(2026, 11, 1)
        self.assertTrue(can_request_cancellation("approved", start_date=date(2026, 11, 5), today=today))
        self.assertFalse(can_request_cancellation("approved", start_date=date(2026, 10, 30), today=today))


if __name__ == "__main__":
    unittest.main()
