"""Unit test suite for Model 2 (Qwen 14B) ELM module."""
from datetime import date
from django.test import TestCase
from modules.leave.domain import rules


class ELMQwen14BTests(TestCase):
    def test_counting_boundaries(self):
        """EL/COL/VL continuous vs CL/RH/SCL working days."""
        d1 = date(2026, 11, 2)  # Monday
        d2 = date(2026, 11, 8)  # Sunday (7 days total)
        el_days = rules.calculate_days("EL", d1, d2)
        cl_days = rules.calculate_days("CL", d1, d2)
        self.assertEqual(el_days, 7.0)
        self.assertEqual(cl_days, 5.0)  # Excludes Sat & Sun

    def test_half_day_first_and_second_half(self):
        """First and second halves on same date are permitted (BR-EL-012)."""
        d = date(2026, 11, 10)
        overlap = rules.check_applicant_overlap(
            d, d, True, "FIRST_HALF",
            d, d, True, "SECOND_HALF"
        )
        self.assertFalse(overlap)

    def test_faculty_vl_year_end_execution(self):
        """VL converts 2:1 into EL and lapses to 0 (BR-EL-007, BR-EL-008)."""
        balances = {"CL": 2.0, "RH": 1.0, "SCL": 4.0, "EL": 10.0, "VL": 55.0, "COL": 20.0}
        updated, notes = rules.execute_year_end_processing("faculty", balances)
        self.assertEqual(updated["CL"], 0.0)
        self.assertEqual(updated["VL"], 0.0)
        self.assertEqual(updated["EL"], 37.5)  # 10 + 27.5
        self.assertEqual(updated["COL"], 20.0)
