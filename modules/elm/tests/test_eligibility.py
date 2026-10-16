import unittest

from modules.elm.domain.entities import LeaveCategory
from modules.elm.domain.errors import IneligibleCategoryError
from modules.elm.domain.policy import validate_category_eligibility


class TestCategoryEligibility(unittest.TestCase):
    def test_faculty_can_use_vl(self):
        self.assertIsNone(
            validate_category_eligibility(
                LeaveCategory.VL, is_faculty=True
            )
        )

    def test_nonfaculty_cannot_use_vl(self):
        with self.assertRaises(IneligibleCategoryError):
            validate_category_eligibility(
                LeaveCategory.VL, is_faculty=False
            )

    def test_vl_requires_explicit_faculty_status(self):
        with self.assertRaises(TypeError):
            validate_category_eligibility(LeaveCategory.VL)

    def test_eligible_employee_can_use_col(self):
        self.assertIsNone(
            validate_category_eligibility(
                LeaveCategory.COL, col_eligible=True
            )
        )

    def test_ineligible_employee_cannot_use_col(self):
        with self.assertRaises(IneligibleCategoryError):
            validate_category_eligibility(
                LeaveCategory.COL, col_eligible=False
            )

    def test_col_requires_explicit_eligibility(self):
        with self.assertRaises(TypeError):
            validate_category_eligibility(LeaveCategory.COL)

    def test_other_categories_need_no_extra_eligibility_argument(self):
        for category in (
            LeaveCategory.CL,
            LeaveCategory.RH,
            LeaveCategory.SCL,
            LeaveCategory.EL,
        ):
            with self.subTest(category=category):
                self.assertIsNone(
                    validate_category_eligibility(category)
                )

    def test_invalid_category_type_is_rejected(self):
        with self.assertRaises(TypeError):
            validate_category_eligibility("VL")


if __name__ == "__main__":
    unittest.main()
