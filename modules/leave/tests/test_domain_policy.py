import unittest
from decimal import Decimal
from datetime import date
from modules.leave.domain.categories import (
    CL, RH, SCL, EL, VL, COL,
    is_eligible_for_category, get_annual_entitlement
)
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.year_end import calculate_year_end_adjustments

class TestDomainPolicy(unittest.TestCase):

    def test_is_eligible_for_category(self):
        self.assertTrue(is_eligible_for_category(CL, 'Faculty'))
        self.assertTrue(is_eligible_for_category(RH, 'Faculty'))
        self.assertTrue(is_eligible_for_category(SCL, 'Faculty'))
        self.assertTrue(is_eligible_for_category(VL, 'Faculty'))
        self.assertTrue(is_eligible_for_category(COL, 'Faculty'))

        self.assertTrue(is_eligible_for_category(CL, 'Staff'))
        self.assertTrue(is_eligible_for_category(RH, 'Staff'))
        self.assertTrue(is_eligible_for_category(SCL, 'Staff'))
        self.assertTrue(is_eligible_for_category(EL, 'Staff'))
        self.assertTrue(is_eligible_for_category(COL, 'Staff'))

        self.assertFalse(is_eligible_for_category(VL, 'Staff'))

    def test_continuous_counting_el_col_vl(self):
        start_date = date(2026, 10, 16)
        end_date = date(2026, 10, 19)
        self.assertEqual(calculate_leave_days(EL, start_date, end_date), Decimal("4"))
        self.assertEqual(calculate_leave_days(COL, start_date, end_date), Decimal("4"))
        self.assertEqual(calculate_leave_days(VL, start_date, end_date), Decimal("4"))

    def test_working_day_counting_cl_weekends(self):
        start_date = date(2026, 10, 16)
        end_date = date(2026, 10, 19)
        self.assertEqual(calculate_leave_days(CL, start_date, end_date), Decimal("2"))

    def test_working_day_counting_cl_with_closed_holiday(self):
        start_date = date(2026, 10, 13)
        end_date = date(2026, 10, 16)
        closed_holidays = {date(2026, 10, 14)}
        self.assertEqual(calculate_leave_days(CL, start_date, end_date, closed_holidays=closed_holidays), Decimal("3"))

    def test_half_day_cl(self):
        start_date = date(2026, 10, 16)
        end_date = date(2026, 10, 16)
        self.assertEqual(calculate_leave_days(CL, start_date, end_date, half_day_type='first_half'), Decimal("0.5"))
        self.assertEqual(calculate_leave_days(CL, start_date, end_date, half_day_type='second_half'), Decimal("0.5"))

        with self.assertRaises(ValueError):
            calculate_leave_days(EL, start_date, end_date, half_day_type='first_half')

        with self.assertRaises(ValueError):
            calculate_leave_days(CL, date(2026, 10, 15), date(2026, 10, 17), half_day_type='first_half')

    def test_rh_restricted_holiday(self):
        start_date = date(2026, 10, 20)
        end_date = date(2026, 10, 20)
        rh_holidays = {'2026-10-20'}
        self.assertEqual(calculate_leave_days(RH, start_date, end_date, rh_holidays=rh_holidays), Decimal("1.0"))
        with self.assertRaises(ValueError):
            calculate_leave_days(RH, date(2026, 10, 21), date(2026, 10, 21), rh_holidays={'2026-10-20'})

    def test_invalid_dates_end_before_start(self):
        with self.assertRaises(ValueError):
            calculate_leave_days(CL, date(2026, 10, 20), date(2026, 10, 16))

    def test_year_end_faculty_conversion(self):
        current_balances = {'CL': 5, 'RH': 2, 'SCL': 10, 'VL': 60, 'EL': 4, 'COL': 10}
        res = calculate_year_end_adjustments(current_balances, is_faculty=True)
        self.assertEqual(res['CL'], Decimal("0"))
        self.assertEqual(res['RH'], Decimal("0"))
        self.assertEqual(res['SCL'], Decimal("0"))
        self.assertEqual(res['carried_forward_el'], Decimal("34"))
        self.assertEqual(res['converted_el'], Decimal("30"))
        self.assertEqual(res['VL'], Decimal("0"))

    def test_year_end_staff_carry_forward(self):
        current_balances = {'CL': 3, 'RH': 1, 'SCL': 5, 'EL': 12, 'COL': 8}
        res = calculate_year_end_adjustments(current_balances, is_faculty=False)
        self.assertEqual(res['carried_forward_el'], Decimal("12"))
        self.assertEqual(res['carried_forward_col'], Decimal("8"))
        self.assertEqual(res['EL'], Decimal("42"))

if __name__ == '__main__':
    unittest.main()
