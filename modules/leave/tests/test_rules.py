"""Unit and integration tests for ELM module."""
from datetime import date
from django.test import TestCase
from modules.leave.domain import rules
from modules.leave.models import LeavePolicy, LeaveBalance, HolidayCalendar


class ELMDomainRulesTests(TestCase):
    def test_continuous_counting_rules(self):
        """BR-EL-011: EL/COL/VL are continuous; CL/RH/SCL exclude weekends/holidays."""
        self.assertTrue(rules.is_continuous_leave_category("EL"))
        self.assertTrue(rules.is_continuous_leave_category("COL"))
        self.assertTrue(rules.is_continuous_leave_category("VL"))
        self.assertFalse(rules.is_continuous_leave_category("CL"))
        self.assertFalse(rules.is_continuous_leave_category("RH"))
        self.assertFalse(rules.is_continuous_leave_category("SCL"))

    def test_half_day_cl_calculation(self):
        """BR-EL-010: Half day CL consumes exactly 0.5 days."""
        d = date(2026, 10, 15)
        charge = rules.calculate_chargeable_days("CL", d, d, is_half_day=True)
        self.assertEqual(charge, 0.5)

    def test_non_overlapping_cl_halves(self):
        """BR-EL-012: First half and second half CL on same date are non-overlapping."""
        d = date(2026, 10, 15)
        overlap = rules.check_leave_overlap(
            new_start=d, new_end=d, new_is_half_day=True, new_half_type="FIRST_HALF",
            existing_start=d, existing_end=d, existing_is_half_day=True, existing_half_type="SECOND_HALF"
        )
        self.assertFalse(overlap)

    def test_vl_to_el_year_end_conversion(self):
        """BR-EL-007, BR-EL-008: 2 VL = 1 EL with fractional conversion preserved."""
        rem_vl, converted_el = rules.convert_vl_to_el_at_year_end(45.0)
        self.assertEqual(rem_vl, 0.0)
        self.assertEqual(converted_el, 22.5)

    def test_year_end_lapse_and_carry_forward(self):
        """BR-EL-002, 003, 004, 005: CL/RH/SCL lapse; EL carries forward."""
        balances = {"CL": 3.0, "RH": 1.0, "SCL": 5.0, "EL": 20.0, "VL": 30.0, "COL": 15.0}
        new_balances = rules.process_year_end_lapse_and_carry_forward("faculty", balances)
        self.assertEqual(new_balances["CL"], 0.0)
        self.assertEqual(new_balances["RH"], 0.0)
        self.assertEqual(new_balances["SCL"], 0.0)
        self.assertEqual(new_balances["VL"], 0.0)
        self.assertEqual(new_balances["EL"], 35.0)  # 20 + 15 from VL
        self.assertEqual(new_balances["COL"], 15.0)
