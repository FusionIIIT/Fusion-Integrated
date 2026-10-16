import unittest
from decimal import Decimal

from modules.elm.domain.entities import LeaveCategory
from modules.elm.domain.policy import get_annual_limit


class TestAnnualLeaveLimits(unittest.TestCase):
    def test_fixed_limits(self):
        expected = {
            LeaveCategory.CL: Decimal("8"),
            LeaveCategory.RH: Decimal("2"),
            LeaveCategory.SCL: Decimal("15"),
        }
        for category, limit in expected.items():
            with self.subTest(category=category.value):
                self.assertEqual(get_annual_limit(category), limit)

    def test_nonfaculty_el_limit(self):
        self.assertEqual(
            get_annual_limit(LeaveCategory.EL, is_faculty=False),
            Decimal("30"),
        )

    def test_faculty_el_limit_is_not_invented(self):
        with self.assertRaises(ValueError):
            get_annual_limit(LeaveCategory.EL, is_faculty=True)

    def test_faculty_vl_limit(self):
        self.assertEqual(
            get_annual_limit(LeaveCategory.VL, is_faculty=True),
            Decimal("60"),
        )

    def test_nonfaculty_vl_is_rejected(self):
        with self.assertRaises(ValueError):
            get_annual_limit(LeaveCategory.VL, is_faculty=False)

    def test_col_requires_eligibility(self):
        self.assertEqual(
            get_annual_limit(LeaveCategory.COL, col_eligible=True),
            Decimal("20"),
        )
        with self.assertRaises(TypeError):
            get_annual_limit(LeaveCategory.COL)
        with self.assertRaises(ValueError):
            get_annual_limit(LeaveCategory.COL, col_eligible=False)

    def test_invalid_argument_types(self):
        with self.assertRaises(TypeError):
            get_annual_limit("CL")
        with self.assertRaises(TypeError):
            get_annual_limit(LeaveCategory.EL, is_faculty=1)
        with self.assertRaises(TypeError):
            get_annual_limit(LeaveCategory.COL, col_eligible=1)


if __name__ == "__main__":
    unittest.main()
