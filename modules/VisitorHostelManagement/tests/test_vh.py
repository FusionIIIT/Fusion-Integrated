"""Unit tests for Visitor Hostel Management domain and logic."""
import unittest
from datetime import date
from decimal import Decimal

from modules.VisitorHostelManagement.domain import (
    check_date_overlap,
    compute_cancellation_charge,
    compute_meal_cost,
    compute_stay_days,
    is_inventory_low,
    is_no_show,
    is_overstay,
)
from modules.VisitorHostelManagement.registry import (
    MODULE,
    PERMISSIONS,
    ROLE_GRANTS,
    SYSTEM_PERMISSIONS,
)


class CancellationLogicTests(unittest.TestCase):
    """Test cancellation fee schedule (BR-VH-006..009)."""

    def test_cancellation_seven_or_more_days_is_free(self):
        check_in = date(2026, 11, 15)
        cancel_date = date(2026, 11, 8)  # Exactly 7 days
        charge = compute_cancellation_charge(check_in, cancel_date, Decimal("1000.00"))
        self.assertEqual(charge, Decimal("0.00"))

        early_cancel = date(2026, 11, 1)  # 14 days
        charge_early = compute_cancellation_charge(check_in, early_cancel, Decimal("1000.00"))
        self.assertEqual(charge_early, Decimal("0.00"))

    def test_cancellation_within_seven_days_is_twenty_five_percent(self):
        check_in = date(2026, 11, 15)
        cancel_date = date(2026, 11, 11)  # 4 days before
        charge = compute_cancellation_charge(check_in, cancel_date, Decimal("1000.00"))
        self.assertEqual(charge, Decimal("250.00"))

    def test_same_day_cancellation_is_fifty_percent(self):
        check_in = date(2026, 11, 15)
        cancel_date = date(2026, 11, 15)  # Same day
        charge = compute_cancellation_charge(check_in, cancel_date, Decimal("1000.00"))
        self.assertEqual(charge, Decimal("500.00"))


class StayAndMealCalculationTests(unittest.TestCase):
    """Test stay duration and meal costing rules (BR-VH-026..034)."""

    def test_stay_days_calculation(self):
        self.assertEqual(compute_stay_days(date(2026, 11, 1), date(2026, 11, 4)), 3)
        self.assertEqual(compute_stay_days(date(2026, 11, 1), date(2026, 11, 1)), 1)

    def test_individual_meal_cost(self):
        self.assertEqual(compute_meal_cost("breakfast"), Decimal("50.00"))
        self.assertEqual(compute_meal_cost("lunch"), Decimal("100.00"))
        self.assertEqual(compute_meal_cost("dinner"), Decimal("100.00"))
        self.assertEqual(compute_meal_cost("full_day"), Decimal("250.00"))

    def test_meal_addons(self):
        self.assertEqual(compute_meal_cost("breakfast", "tea"), Decimal("60.00"))
        self.assertEqual(compute_meal_cost("dinner", "milk"), Decimal("115.00"))


class DateOverlapTests(unittest.TestCase):
    """Test room availability and booking date overlap (BR-VH-004)."""

    def test_overlapping_ranges(self):
        self.assertTrue(
            check_date_overlap(
                date(2026, 11, 1), date(2026, 11, 5),
                date(2026, 11, 3), date(2026, 11, 7)
            )
        )

    def test_disjoint_ranges(self):
        self.assertFalse(
            check_date_overlap(
                date(2026, 11, 1), date(2026, 11, 5),
                date(2026, 11, 5), date(2026, 11, 8)
            )
        )
        self.assertFalse(
            check_date_overlap(
                date(2026, 11, 1), date(2026, 11, 3),
                date(2026, 11, 5), date(2026, 11, 8)
            )
        )


class StayAlertExceptionTests(unittest.TestCase):
    """Test no-show and overstay detection (BR-VH-017, BR-VH-018, BR-VH-041)."""

    def test_no_show_detection(self):
        self.assertTrue(is_no_show("approved", date(2026, 11, 1), date(2026, 11, 2)))
        self.assertFalse(is_no_show("approved", date(2026, 11, 5), date(2026, 11, 2)))
        self.assertFalse(is_no_show("checked_in", date(2026, 11, 1), date(2026, 11, 2)))

    def test_overstay_detection(self):
        self.assertTrue(is_overstay("checked_in", date(2026, 11, 3), date(2026, 11, 4)))
        self.assertFalse(is_overstay("checked_in", date(2026, 11, 5), date(2026, 11, 4)))
        self.assertFalse(is_overstay("checked_out", date(2026, 11, 3), date(2026, 11, 4)))

    def test_inventory_threshold(self):
        self.assertTrue(is_inventory_low(5, 10))
        self.assertTrue(is_inventory_low(10, 10))
        self.assertFalse(is_inventory_low(15, 10))


class RegistryPermissionsTests(unittest.TestCase):
    """Test registry declarations and role grants."""

    def test_module_metadata(self):
        self.assertEqual(MODULE["code"], "visitor_hostel")
        self.assertEqual(MODULE["base_path"], "/visitor-hostel")

    def test_permissions_are_granted_or_system(self):
        all_perms = {code for code, _ in PERMISSIONS}
        granted = {code for codes in ROLE_GRANTS.values() for code in codes}
        system = set(SYSTEM_PERMISSIONS)
        self.assertEqual(all_perms - granted - system, set())


if __name__ == "__main__":
    unittest.main()
