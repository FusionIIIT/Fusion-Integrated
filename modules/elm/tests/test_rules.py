from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from modules.elm.domain.rules import count_leave_days, entitlement_for


class LeaveRuleTests(SimpleTestCase):
    def test_weekdays_exclude_weekends_and_closed_dates(self):
        # Monday 12 October through Sunday 18 October 2026.
        days = count_leave_days(
            "CL",
            date(2026, 10, 12),
            date(2026, 10, 18),
            closed_dates={date(2026, 10, 14)},
        )
        self.assertEqual(days, Decimal("4"))

    def test_continuous_leave_counts_weekends(self):
        days = count_leave_days("EL", date(2026, 10, 16), date(2026, 10, 19))
        self.assertEqual(days, Decimal("4"))

    def test_policy_can_override_continuous_counting_mode(self):
        period_start = date(2026, 10, 16)
        period_end = date(2026, 10, 19)
        continuous = count_leave_days("EL", period_start, period_end, continuous_counting=True)
        working_days = count_leave_days("EL", period_start, period_end, continuous_counting=False)
        self.assertEqual(continuous, Decimal("4"))
        self.assertEqual(working_days, Decimal("2"))

    def test_cl_half_day_counts_half(self):
        days = count_leave_days("CL", date(2026, 10, 12), date(2026, 10, 12), cl_half="first")
        self.assertEqual(days, Decimal("0.50"))

    def test_restricted_holiday_must_be_one_day(self):
        with self.assertRaises(ValueError):
            count_leave_days("RH", date(2026, 10, 12), date(2026, 10, 13))

    def test_restricted_holiday_counts_even_if_marked_closed(self):
        days = count_leave_days(
            "RH",
            date(2026, 10, 12),
            date(2026, 10, 12),
            closed_dates={date(2026, 10, 12)},
        )
        self.assertEqual(days, Decimal("1.00"))

    def test_half_day_cl_is_not_counted_on_weekend_or_closure(self):
        weekend = count_leave_days("CL", date(2026, 10, 17), date(2026, 10, 17), cl_half="first")
        closed = count_leave_days(
            "CL",
            date(2026, 10, 12),
            date(2026, 10, 12),
            closed_dates={date(2026, 10, 12)},
            cl_half="second",
        )
        self.assertEqual(weekend, Decimal("0.00"))
        self.assertEqual(closed, Decimal("0.00"))

    def test_invalid_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            count_leave_days("EL", date(2026, 10, 13), date(2026, 10, 12))

    def test_entitlement_is_employee_scoped_for_el_and_vl(self):
        self.assertEqual(entitlement_for("EL", "faculty"), Decimal("0.00"))
        self.assertEqual(entitlement_for("EL", "staff"), Decimal("30.00"))
        self.assertEqual(entitlement_for("VL", "staff"), Decimal("0.00"))
        self.assertEqual(entitlement_for("VL", "faculty"), Decimal("60.00"))
