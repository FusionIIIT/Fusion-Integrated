"""Domain tests for ELM leave-day counting rules.

Pure Python, no database.
Verifies BR-EL-010 (Half-day CL) and BR-EL-011 (Continuous-day counting).
"""
import datetime
import unittest

from modules.elm.domain.constants import HalfDayPeriod, LeaveCategory
from modules.elm.domain.counting import (
    InvalidDateRange,
    InvalidHalfDayRequest,
    calculate_chargeable_days,
    is_weekend,
)


class TestLeaveCounting(unittest.TestCase):

    def setUp(self):
        # 2026-10-23 is Friday
        # 2026-10-24 is Saturday
        # 2026-10-25 is Sunday
        # 2026-10-26 is Monday
        # 2026-10-27 is Tuesday (suppose closed holiday)
        # 2026-10-28 is Wednesday
        self.fri = datetime.date(2026, 10, 23)
        self.sat = datetime.date(2026, 10, 24)
        self.sun = datetime.date(2026, 10, 25)
        self.mon = datetime.date(2026, 10, 26)
        self.tue_holiday = datetime.date(2026, 10, 27)
        self.wed = datetime.date(2026, 10, 28)
        self.closed_holidays = {self.tue_holiday}

    def test_weekend_helper(self):
        self.assertFalse(is_weekend(self.fri))
        self.assertTrue(is_weekend(self.sat))
        self.assertTrue(is_weekend(self.sun))
        self.assertFalse(is_weekend(self.mon))

    def test_continuous_counting_for_el_col_vl(self):
        """BR-EL-011: For EL, COL, VL, weekends and closed holidays within interval ARE counted."""
        # Span: Friday 23 to Wednesday 28 (6 calendar days: Fri, Sat, Sun, Mon, Tue[holiday], Wed)
        days_el = calculate_chargeable_days(
            LeaveCategory.EL, self.fri, self.wed, closed_holidays=self.closed_holidays
        )
        self.assertEqual(days_el, 6.0)

        days_col = calculate_chargeable_days(
            LeaveCategory.COL, self.fri, self.wed, closed_holidays=self.closed_holidays
        )
        self.assertEqual(days_col, 6.0)

        days_vl = calculate_chargeable_days(
            LeaveCategory.VL, self.fri, self.wed, closed_holidays=self.closed_holidays
        )
        self.assertEqual(days_vl, 6.0)

    def test_working_day_counting_for_cl_scl_rh(self):
        """BR-EL-011: For CL, SCL, RH, intervening weekends and closed holidays are EXCLUDED."""
        # Span: Friday 23 to Wednesday 28:
        # Fri: working (1)
        # Sat: weekend (0)
        # Sun: weekend (0)
        # Mon: working (1)
        # Tue: closed holiday (0)
        # Wed: working (1)
        # Total working days = 3!
        days_cl = calculate_chargeable_days(
            LeaveCategory.CL, self.fri, self.wed, closed_holidays=self.closed_holidays
        )
        self.assertEqual(days_cl, 3.0)

        days_scl = calculate_chargeable_days(
            LeaveCategory.SCL, self.fri, self.wed, closed_holidays=self.closed_holidays
        )
        self.assertEqual(days_scl, 3.0)

        days_rh = calculate_chargeable_days(
            LeaveCategory.RH, self.fri, self.wed, closed_holidays=self.closed_holidays
        )
        self.assertEqual(days_rh, 3.0)

    def test_half_day_cl_first_and_second_half(self):
        """BR-EL-010: Half-day CL consumes exactly 0.5 day."""
        days_first = calculate_chargeable_days(
            category=LeaveCategory.CL,
            start_date=self.mon,
            end_date=self.mon,
            is_half_day=True,
            half_day_period=HalfDayPeriod.FIRST_HALF,
        )
        self.assertEqual(days_first, 0.5)

        days_second = calculate_chargeable_days(
            category=LeaveCategory.CL,
            start_date=self.mon,
            end_date=self.mon,
            is_half_day=True,
            half_day_period=HalfDayPeriod.SECOND_HALF,
        )
        self.assertEqual(days_second, 0.5)

    def test_half_day_cl_validation_errors(self):
        """Reject invalid half-day requests."""
        # 1. Non-CL category with half-day
        with self.assertRaises(InvalidHalfDayRequest):
            calculate_chargeable_days(
                category=LeaveCategory.EL,
                start_date=self.mon,
                end_date=self.mon,
                is_half_day=True,
                half_day_period=HalfDayPeriod.FIRST_HALF,
            )

        # 2. Multi-day span with half-day
        with self.assertRaises(InvalidHalfDayRequest):
            calculate_chargeable_days(
                category=LeaveCategory.CL,
                start_date=self.mon,
                end_date=self.wed,
                is_half_day=True,
                half_day_period=HalfDayPeriod.FIRST_HALF,
            )

        # 3. Missing half_day_period (NONE)
        with self.assertRaises(InvalidHalfDayRequest):
            calculate_chargeable_days(
                category=LeaveCategory.CL,
                start_date=self.mon,
                end_date=self.mon,
                is_half_day=True,
                half_day_period=HalfDayPeriod.NONE,
            )

    def test_invalid_date_range_raises(self):
        """start_date after end_date raises InvalidDateRange."""
        with self.assertRaises(InvalidDateRange):
            calculate_chargeable_days(LeaveCategory.CL, self.wed, self.fri)


if __name__ == "__main__":
    unittest.main()
