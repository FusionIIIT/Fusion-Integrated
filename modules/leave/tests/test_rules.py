"""Unit tests for Employee Leave Management (ELM) domain rules."""
from datetime import date
import unittest

from modules.leave.domain.rules import (
    get_annual_entitlement,
    is_carry_forward_allowed,
    calculate_leave_days,
    convert_vl_to_el,
    validate_substitute,
    check_leave_overlap,
    can_cancel_leave,
    HALF_DAY_FIRST,
    HALF_DAY_SECOND,
    HALF_DAY_NONE,
)


class TestLeaveRules(unittest.TestCase):
    def test_entitlements(self):
        # Faculty gets 60 VL, 0 EL (BR-EL-006)
        self.assertEqual(get_annual_entitlement("VL", is_faculty=True), 60.0)
        self.assertEqual(get_annual_entitlement("EL", is_faculty=True), 0.0)
        # Non-faculty gets 30 EL, 0 VL (BR-EL-005)
        self.assertEqual(get_annual_entitlement("EL", is_faculty=False), 30.0)
        self.assertEqual(get_annual_entitlement("VL", is_faculty=False), 0.0)

    def test_carry_forward(self):
        # Only EL and COL carry forward
        self.assertTrue(is_carry_forward_allowed("EL"))
        self.assertTrue(is_carry_forward_allowed("COL"))
        self.assertFalse(is_carry_forward_allowed("CL"))

    def test_half_day_and_continuous_counting(self):
        d = date(2026, 10, 12)
        # Half day CL is 0.5 (BR-EL-010)
        self.assertEqual(calculate_leave_days("CL", d, d, HALF_DAY_FIRST), 0.5)

        # Continuous counting for EL (Fri to Mon = 4 days) (BR-EL-011)
        fri = date(2026, 10, 9)
        mon = date(2026, 10, 12)
        self.assertEqual(calculate_leave_days("EL", fri, mon), 4.0)
        # Working day counting for CL (Fri to Mon = 2 working days)
        self.assertEqual(calculate_leave_days("CL", fri, mon), 2.0)

    def test_substitute_validation(self):
        # Cannot substitute oneself (BR-EL-014)
        self.assertFalse(validate_substitute(1, 1))
        self.assertTrue(validate_substitute(1, 2))

    def test_leave_overlap_exception(self):
        d = date(2026, 11, 2)
        existing = [{"start_date": d, "end_date": d, "half_day_period": HALF_DAY_FIRST}]
        # First half + second half on same day does not overlap (BR-EL-012)
        self.assertFalse(check_leave_overlap(existing, d, d, HALF_DAY_SECOND))
        # First half + first half overlaps
        self.assertTrue(check_leave_overlap(existing, d, d, HALF_DAY_FIRST))

    def test_cancellation_pre_start(self):
        start = date(2026, 10, 15)
        # Can cancel strictly before start date (BR-EL-023)
        self.assertTrue(can_cancel_leave(start, date(2026, 10, 14)))
        self.assertFalse(can_cancel_leave(start, date(2026, 10, 15)))


if __name__ == "__main__":
    unittest.main()
