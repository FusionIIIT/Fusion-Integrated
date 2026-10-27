"""Unit tests for ELM pure domain policy calculations (BR-EL-001 to BR-EL-038)."""
import datetime
from decimal import Decimal
import unittest

from modules.elm.domain.errors import (
    CalendarValidationError,
    EligibilityError,
    ELMValidationError,
)
from modules.elm.domain.policy import (
    calculate_leave_duration,
    calculate_resumption_adjustment,
    check_date_overlap,
    convert_vl_to_el,
    validate_eligibility,
    validate_rh_calendar,
    validate_vl_vacation_window,
)


class TestDomainPolicy(unittest.TestCase):
    def test_cl_half_day_duration(self):
        d = datetime.date(2026, 11, 4)  # Wednesday
        duration = calculate_leave_duration("CL", d, d, is_half_day=True, half_day_type="first_half")
        self.assertEqual(duration, Decimal("0.5"))

    def test_el_continuous_counting_includes_weekend(self):
        # Friday to Monday = 4 calendar days (Fri, Sat, Sun, Mon)
        start = datetime.date(2026, 11, 6)
        end = datetime.date(2026, 11, 9)
        duration = calculate_leave_duration("EL", start, end)
        self.assertEqual(duration, Decimal("4.0"))

    def test_cl_working_day_counting_excludes_weekend(self):
        # Friday to Monday = 2 working days (Fri, Mon)
        start = datetime.date(2026, 11, 6)
        end = datetime.date(2026, 11, 9)
        duration = calculate_leave_duration("CL", start, end)
        self.assertEqual(duration, Decimal("2.0"))

    def test_cl_working_day_counting_excludes_closed_holiday(self):
        start = datetime.date(2026, 11, 4)  # Wednesday
        end = datetime.date(2026, 11, 6)    # Friday
        holidays = {datetime.date(2026, 11, 5)}  # Thursday is holiday
        duration = calculate_leave_duration("CL", start, end, holiday_calendar=holidays)
        self.assertEqual(duration, Decimal("2.0"))

    def test_rh_calendar_validation_success_and_failure(self):
        rh_dates = {datetime.date(2026, 11, 10), datetime.date(2026, 12, 24)}
        # Valid date
        validate_rh_calendar(datetime.date(2026, 11, 10), rh_dates)
        # Invalid date
        with self.assertRaises(CalendarValidationError):
            validate_rh_calendar(datetime.date(2026, 11, 11), rh_dates)

    def test_vl_vacation_window_validation(self):
        vacations = [
            (datetime.date(2026, 5, 1), datetime.date(2026, 6, 30)),
            (datetime.date(2026, 12, 15), datetime.date(2026, 12, 31)),
        ]
        # Inside vacation
        validate_vl_vacation_window(datetime.date(2026, 5, 10), datetime.date(2026, 5, 20), vacations)
        # Outside vacation
        with self.assertRaises(CalendarValidationError):
            validate_vl_vacation_window(datetime.date(2026, 7, 1), datetime.date(2026, 7, 10), vacations)

    def test_date_overlap_detection(self):
        s1 = datetime.date(2026, 11, 2)
        e1 = datetime.date(2026, 11, 5)
        s2 = datetime.date(2026, 11, 4)
        e2 = datetime.date(2026, 11, 8)
        self.assertTrue(check_date_overlap(s1, e1, None, s2, e2, None))

        # Disjoint
        s3 = datetime.date(2026, 11, 10)
        e3 = datetime.date(2026, 11, 12)
        self.assertFalse(check_date_overlap(s1, e1, None, s3, e3, None))

    def test_same_date_complementary_half_day_cl_not_overlapping(self):
        d = datetime.date(2026, 11, 4)
        overlap = check_date_overlap(d, d, "first_half", d, d, "second_half")
        self.assertFalse(overlap)

    def test_same_date_identical_half_day_cl_is_overlapping(self):
        d = datetime.date(2026, 11, 4)
        overlap = check_date_overlap(d, d, "first_half", d, d, "first_half")
        self.assertTrue(overlap)

    def test_vl_to_el_year_end_conversion_fractional(self):
        # 15 VL converts to 7.5 EL (2:1 ratio)
        converted = convert_vl_to_el(Decimal("15.0"))
        self.assertEqual(converted, Decimal("7.5"))

    def test_resumption_adjustment_normal(self):
        # Approved 10 to 14, resumed on 15 (on time)
        start = datetime.date(2026, 11, 10)
        end = datetime.date(2026, 11, 14)
        resumed = datetime.date(2026, 11, 15)
        rtype, delta, taken = calculate_resumption_adjustment(start, end, resumed, "EL")
        self.assertEqual(rtype, "NORMAL")
        self.assertEqual(delta, Decimal("0.0"))
        self.assertEqual(taken, Decimal("5.0"))

    def test_resumption_adjustment_early(self):
        # Approved 10 to 14 (5 days), resumed on 13 (took 10 to 12 = 3 days, 2 days credited back)
        start = datetime.date(2026, 11, 10)
        end = datetime.date(2026, 11, 14)
        resumed = datetime.date(2026, 11, 13)
        rtype, delta, taken = calculate_resumption_adjustment(start, end, resumed, "EL")
        self.assertEqual(rtype, "EARLY")
        self.assertEqual(delta, Decimal("2.0"))
        self.assertEqual(taken, Decimal("3.0"))

    def test_resumption_adjustment_late(self):
        # Approved 10 to 14 (5 days), expected 15, resumed on 17 (2 extra days taken: 15, 16)
        start = datetime.date(2026, 11, 10)
        end = datetime.date(2026, 11, 14)
        resumed = datetime.date(2026, 11, 17)
        rtype, delta, taken = calculate_resumption_adjustment(start, end, resumed, "EL")
        self.assertEqual(rtype, "LATE")
        self.assertEqual(delta, Decimal("-2.0"))
        self.assertEqual(taken, Decimal("7.0"))

    def test_staff_cannot_apply_for_vl(self):
        with self.assertRaises(EligibilityError):
            validate_eligibility("staff", "VL")

    def test_faculty_can_apply_for_vl(self):
        validate_eligibility("faculty", "VL")


if __name__ == "__main__":
    unittest.main()
