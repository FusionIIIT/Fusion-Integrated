"""Unit tests for Employee Leave Management (ELM) domain rules.

Validates business rules BR-EL-001 through BR-EL-014 and AFR requirements:
- BR-EL-014: Substitute validation (no self-nomination)
- BR-EL-010: Half-day CL duration and constraints
- BR-EL-011: Continuous vs non-continuous leave counting and interval ordering
- BR-EL-012: Overlap check with half-day CL exception
- AFR-EL-001.1 / Manifest: Action permissions mapping
"""
from __future__ import annotations

import unittest
from datetime import date

from modules.leave.domain.rules import (
    ACTION_PERMISSIONS,
    ANNUAL_ENTITLEMENTS,
    SUPPORTED_CATEGORIES,
    calculate_chargeable_days,
    do_intervals_overlap,
    is_half_day_cl_valid,
    is_overlap_valid,
    is_substitute_valid,
)


class TestSubstituteValidation(unittest.TestCase):
    """Test BR-EL-014: Substitute must be another employee and not the applicant."""

    def test_substitute_different_from_applicant_is_valid(self):
        self.assertTrue(is_substitute_valid(applicant_id=101, substitute_id=102))

    def test_substitute_same_as_applicant_is_rejected(self):
        self.assertFalse(is_substitute_valid(applicant_id=101, substitute_id=101))

    def test_substitute_none_is_valid(self):
        self.assertTrue(is_substitute_valid(applicant_id=101, substitute_id=None))
        self.assertTrue(is_substitute_valid(applicant_id=None, substitute_id=None))


class TestChargeableDaysCalculation(unittest.TestCase):
    """Test BR-EL-010, BR-EL-011, and AFR-EL-003.3 leave duration calculations."""

    def test_half_day_cl_consumes_half_day(self):
        d = date(2026, 11, 2)  # Monday
        self.assertEqual(
            calculate_chargeable_days("CL", d, d, half_day_cl=True),
            0.5,
        )

    def test_continuous_counting_includes_weekends_and_holidays(self):
        # 2026-11-06 (Friday) to 2026-11-09 (Monday) = 4 calendar days
        start = date(2026, 11, 6)
        end = date(2026, 11, 9)
        holiday = {date(2026, 11, 6)}

        # Continuous categories: EL, COL, VL
        for category in ("EL", "COL", "VL"):
            days = calculate_chargeable_days(
                category=category,
                start_date=start,
                end_date=end,
                holidays=holiday,
            )
            self.assertEqual(days, 4.0)

    def test_non_continuous_counting_excludes_weekends(self):
        # 2026-11-06 (Friday) to 2026-11-09 (Monday): Sat & Sun excluded -> 2 working days
        start = date(2026, 11, 6)
        end = date(2026, 11, 9)

        # Non-continuous categories: CL, SCL, RH
        for category in ("CL", "SCL", "RH"):
            days = calculate_chargeable_days(category, start, end)
            self.assertEqual(days, 2.0)

    def test_non_continuous_counting_excludes_declared_holidays(self):
        # Mon (2026-11-02) to Fri (2026-11-06): 5 working days, minus 1 holiday -> 4 days
        start = date(2026, 11, 2)
        end = date(2026, 11, 6)
        holidays = {date(2026, 11, 4)}  # Wednesday is holiday
        days = calculate_chargeable_days("CL", start, end, holidays=holidays)
        self.assertEqual(days, 4.0)

    def test_weekend_only_interval(self):
        # Saturday to Sunday: non-continuous is 0 days, continuous is 2 days
        sat = date(2026, 11, 7)
        sun = date(2026, 11, 8)
        self.assertEqual(calculate_chargeable_days("CL", sat, sun), 0.0)
        self.assertEqual(calculate_chargeable_days("EL", sat, sun), 2.0)

    def test_single_day_request(self):
        # Single working day
        mon = date(2026, 11, 2)
        self.assertEqual(calculate_chargeable_days("CL", mon, mon), 1.0)
        self.assertEqual(calculate_chargeable_days("EL", mon, mon), 1.0)

        # Single weekend day
        sat = date(2026, 11, 7)
        self.assertEqual(calculate_chargeable_days("CL", sat, sat), 0.0)
        self.assertEqual(calculate_chargeable_days("EL", sat, sat), 1.0)

    def test_invalid_date_order_raises_value_error(self):
        start = date(2026, 11, 10)
        end = date(2026, 11, 5)
        with self.assertRaises(ValueError):
            calculate_chargeable_days("CL", start, end)


class TestHalfDayCLRules(unittest.TestCase):
    """Test BR-EL-010 half-day Casual Leave constraints."""

    def test_half_day_only_allowed_for_cl(self):
        d = date(2026, 11, 2)
        self.assertTrue(is_half_day_cl_valid(half_day_cl=True, category="CL", start_date=d, end_date=d))
        self.assertFalse(is_half_day_cl_valid(half_day_cl=True, category="EL", start_date=d, end_date=d))
        self.assertFalse(is_half_day_cl_valid(half_day_cl=True, category="RH", start_date=d, end_date=d))

    def test_half_day_requires_matching_start_and_end_date(self):
        start = date(2026, 11, 2)
        end = date(2026, 11, 3)
        self.assertFalse(is_half_day_cl_valid(half_day_cl=True, category="CL", start_date=start, end_date=end))

    def test_full_day_request_is_always_valid_for_half_day_check(self):
        start = date(2026, 11, 2)
        end = date(2026, 11, 5)
        self.assertTrue(is_half_day_cl_valid(half_day_cl=False, category="EL", start_date=start, end_date=end))


class TestOverlapRules(unittest.TestCase):
    """Test BR-EL-011 and BR-EL-012 date ordering and interval overlaps."""

    def test_date_order_validity(self):
        self.assertTrue(is_overlap_valid(date(2026, 11, 2), date(2026, 11, 2)))
        self.assertTrue(is_overlap_valid(date(2026, 11, 2), date(2026, 11, 5)))
        self.assertFalse(is_overlap_valid(date(2026, 11, 5), date(2026, 11, 2)))

    def test_overlapping_intervals_detected(self):
        a_start, a_end = date(2026, 11, 2), date(2026, 11, 6)
        b_start, b_end = date(2026, 11, 4), date(2026, 11, 8)
        self.assertTrue(do_intervals_overlap(a_start, a_end, b_start, b_end))

    def test_non_overlapping_intervals(self):
        a_start, a_end = date(2026, 11, 2), date(2026, 11, 4)
        b_start, b_end = date(2026, 11, 5), date(2026, 11, 8)
        self.assertFalse(do_intervals_overlap(a_start, a_end, b_start, b_end))

    def test_br_el_012_half_day_cl_same_date_exception(self):
        d = date(2026, 11, 2)
        # Two half-day requests on the exact same date do NOT conflict (first & second half)
        self.assertFalse(
            do_intervals_overlap(d, d, d, d, half_day_a=True, half_day_b=True)
        )
        # If one is full-day and one is half-day on same date, they DO overlap
        self.assertTrue(
            do_intervals_overlap(d, d, d, d, half_day_a=False, half_day_b=True)
        )


class TestEntitlementsAndPermissions(unittest.TestCase):
    """Test annual entitlement quotas and permission action mappings."""

    def test_supported_categories(self):
        self.assertEqual(
            set(SUPPORTED_CATEGORIES),
            {"CL", "RH", "SCL", "EL", "COL", "VL"},
        )

    def test_annual_entitlements(self):
        # Fixed non-accumulating statutory quotas (BR-EL-002, BR-EL-003, BR-EL-004)
        self.assertEqual(ANNUAL_ENTITLEMENTS["CL"], 8.0)
        self.assertEqual(ANNUAL_ENTITLEMENTS["RH"], 2.0)
        self.assertEqual(ANNUAL_ENTITLEMENTS["SCL"], 15.0)
        # Carry-forward categories like EL must NOT be in ANNUAL_ENTITLEMENTS
        self.assertNotIn("EL", ANNUAL_ENTITLEMENTS)

    def test_action_permissions_declared(self):
        expected_perms = {
            "leave.application.view",
            "leave.application.create",
            "leave.application.review",
            "leave.application.approve",
            "leave.application.delete",
            "leave.substitute.respond",
            "leave.balance.view",
        }
        self.assertEqual(set(ACTION_PERMISSIONS.values()), expected_perms)


if __name__ == "__main__":
    unittest.main()
