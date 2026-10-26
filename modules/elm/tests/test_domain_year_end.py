"""Domain tests for ELM year-end processing rules.

Pure Python, no database.
Verifies BR-EL-002 through BR-EL-009, including fractional 2:1 VL-to-EL conversion.
"""
import unittest

from modules.elm.domain.year_end import CurrentBalanceSnapshot, compute_year_end_for_employee


class TestYearEndProcessing(unittest.TestCase):

    def test_staff_year_end_rollover(self):
        """Staff (non-faculty): CL/RH/SCL lapse; EL/COL carry forward + 30/20 new credits."""
        old_balances = [
            CurrentBalanceSnapshot(leave_type_code="CL", year=2026, allotted=8.0, used=3.0),   # 5 unused -> lapse
            CurrentBalanceSnapshot(leave_type_code="RH", year=2026, allotted=2.0, used=1.0),   # 1 unused -> lapse
            CurrentBalanceSnapshot(leave_type_code="SCL", year=2026, allotted=15.0, used=5.0), # 10 unused -> lapse
            CurrentBalanceSnapshot(leave_type_code="EL", year=2026, allotted=30.0, used=10.0), # 20 unused -> carry forward + 30 = 50
            CurrentBalanceSnapshot(leave_type_code="COL", year=2026, allotted=20.0, used=4.0), # 16 unused -> carry forward + 20 = 36
        ]

        outcomes = compute_year_end_for_employee(
            balances=old_balances,
            is_faculty=False,
            old_year=2026,
            new_year=2027,
        )
        res_map = {o.leave_type_code: o for o in outcomes}

        # CL lapses (BR-EL-002)
        self.assertEqual(res_map["CL"].lapsed_amount, 5.0)
        self.assertEqual(res_map["CL"].carried_forward, 0.0)
        self.assertEqual(res_map["CL"].new_allotted, 8.0)

        # RH lapses (BR-EL-003)
        self.assertEqual(res_map["RH"].lapsed_amount, 1.0)
        self.assertEqual(res_map["RH"].carried_forward, 0.0)
        self.assertEqual(res_map["RH"].new_allotted, 2.0)

        # SCL lapses (BR-EL-004)
        self.assertEqual(res_map["SCL"].lapsed_amount, 10.0)
        self.assertEqual(res_map["SCL"].carried_forward, 0.0)
        self.assertEqual(res_map["SCL"].new_allotted, 15.0)

        # EL carries forward + 30 new credit (BR-EL-005)
        self.assertEqual(res_map["EL"].carried_forward, 20.0)
        self.assertEqual(res_map["EL"].lapsed_amount, 0.0)
        self.assertEqual(res_map["EL"].new_allotted, 50.0)

        # COL carries forward + 20 new credit (BR-EL-009)
        self.assertEqual(res_map["COL"].carried_forward, 16.0)
        self.assertEqual(res_map["COL"].lapsed_amount, 0.0)
        self.assertEqual(res_map["COL"].new_allotted, 36.0)

    def test_faculty_vl_to_el_fractional_conversion(self):
        """Faculty: Unused VL converts at 2:1 into EL, including fractions (BR-EL-007, BR-EL-008)."""
        # Faculty has 15 unused VL and 10 unused EL
        old_balances = [
            CurrentBalanceSnapshot(leave_type_code="VL", year=2026, allotted=60.0, used=45.0), # 15 unused VL
            CurrentBalanceSnapshot(leave_type_code="EL", year=2026, allotted=20.0, used=10.0), # 10 unused EL
        ]

        outcomes = compute_year_end_for_employee(
            balances=old_balances,
            is_faculty=True,
            old_year=2026,
            new_year=2027,
        )
        res_map = {o.leave_type_code: o for o in outcomes}

        # VL converts at 2:1 -> 15 / 2 = 7.5 EL! (BR-EL-007)
        vl_out = res_map["VL"]
        self.assertEqual(vl_out.unused_amount, 15.0)
        self.assertEqual(vl_out.converted_amount, 7.5)
        self.assertEqual(vl_out.carried_forward, 0.0)  # VL itself does NOT carry forward
        self.assertEqual(vl_out.new_allotted, 60.0)

        # Converted EL (7.5) is credited to EL balance: 10 carry forward + 7.5 converted = 17.5! (BR-EL-008)
        el_out = res_map["EL"]
        self.assertEqual(el_out.carried_forward, 10.0)
        self.assertEqual(el_out.converted_amount, 7.5)
        self.assertEqual(el_out.new_allotted, 17.5)


if __name__ == "__main__":
    unittest.main()
