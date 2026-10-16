import unittest
from datetime import date

from modules.elm.domain.entities import (
    LeaveCategory,
    LeaveRequest,
    LeaveRequestDateRange,
)
from modules.elm.domain.errors import (
    ELMDomainError,
    InvalidDateRangeError,
    IneligibleCategoryError,
    InsufficientBalanceError,
    OverlappingLeaveError,
    InvalidWorkflowTransitionError,
)
from modules.elm.domain.policy import count_continuous_leave_days


class TestLeaveCategory(unittest.TestCase):
    def test_exact_supported_categories(self):
        self.assertEqual(
            [(item.name, item.value) for item in LeaveCategory],
            [
                ("CL", "CL"),
                ("RH", "RH"),
                ("SCL", "SCL"),
                ("EL", "EL"),
                ("COL", "COL"),
                ("VL", "VL"),
            ],
        )


class TestLeaveRequestDateRange(unittest.TestCase):
    def test_valid_date_range(self):
        start = date(2026, 10, 1)
        end = date(2026, 10, 10)
        date_range = LeaveRequestDateRange(start, end)
        self.assertEqual(date_range.start_date, start)
        self.assertEqual(date_range.end_date, end)

    def test_reversed_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            LeaveRequestDateRange(date(2026, 10, 10), date(2026, 10, 1))


class TestLeaveRequest(unittest.TestCase):
    def test_leave_request_creation(self):
        date_range = LeaveRequestDateRange(
            date(2026, 10, 1), date(2026, 10, 10)
        )
        request = LeaveRequest(LeaveCategory.CL, date_range)
        self.assertEqual(request.category, LeaveCategory.CL)
        self.assertEqual(request.date_range, date_range)


class TestELMDomainErrors(unittest.TestCase):
    def test_specific_errors_inherit_from_base(self):
        for exception_type in (
            InvalidDateRangeError,
            IneligibleCategoryError,
            InsufficientBalanceError,
            OverlappingLeaveError,
            InvalidWorkflowTransitionError,
        ):
            with self.subTest(exception=exception_type.__name__):
                self.assertTrue(issubclass(exception_type, ELMDomainError))

    def test_specific_errors_can_be_instantiated(self):
        instances = [
            InvalidDateRangeError(date(2026, 10, 10), date(2026, 10, 1)),
            IneligibleCategoryError("CL"),
            InsufficientBalanceError(2, 5),
            OverlappingLeaveError(object()),
            InvalidWorkflowTransitionError("pending", "approved"),
        ]
        for exception in instances:
            with self.subTest(exception=type(exception).__name__):
                self.assertIsInstance(exception, ELMDomainError)


class TestCountContinuousLeaveDays(unittest.TestCase):
    def test_datetime_boundaries_are_rejected(self):
     from datetime import datetime

     date_range = LeaveRequestDateRange(
        datetime(2026, 10, 1, 9, 0),
        datetime(2026, 10, 2, 9, 0),
    )

     with self.assertRaises(TypeError):
        count_continuous_leave_days(LeaveCategory.EL, date_range)

    def test_supported_categories_count_all_calendar_days(self):
        date_range = LeaveRequestDateRange(
            date(2026, 10, 1), date(2026, 10, 10)
        )
        for category in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
            with self.subTest(category=category.value):
                self.assertEqual(count_continuous_leave_days(category, date_range), 10)

    def test_single_day_interval(self):
        date_range = LeaveRequestDateRange(
            date(2026, 10, 3), date(2026, 10, 3)
        )
        self.assertEqual(
            count_continuous_leave_days(LeaveCategory.EL, date_range), 1
        )

    def test_weekend_is_included(self):
        # Friday through Monday includes Saturday and Sunday.
        date_range = LeaveRequestDateRange(
            date(2026, 10, 2), date(2026, 10, 5)
        )
        self.assertEqual(
            count_continuous_leave_days(LeaveCategory.EL, date_range), 4
        )

    def test_cl_rh_and_scl_are_rejected(self):
        date_range = LeaveRequestDateRange(
            date(2026, 10, 1), date(2026, 10, 10)
        )
        for category in (LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL):
            with self.subTest(category=category.value):
                with self.assertRaises(ValueError):
                    count_continuous_leave_days(category, date_range)

    def test_invalid_argument_types_are_rejected(self):
        date_range = LeaveRequestDateRange(
            date(2026, 10, 1), date(2026, 10, 10)
        )
        with self.assertRaises(TypeError):
            count_continuous_leave_days("EL", date_range)
        with self.assertRaises(TypeError):
            count_continuous_leave_days(LeaveCategory.EL, object())


if __name__ == "__main__":
    unittest.main()
