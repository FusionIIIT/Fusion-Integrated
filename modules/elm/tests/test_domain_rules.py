"""Real, runnable tests for the pure-Python domain layer (no Django needed —
run with: python3 -m unittest modules.elm.tests.test_domain_rules -v).

Django-dependent code (models/selectors/services/api) could NOT be executed
in this environment (see UNRESOLVED.md) and is not covered here.
"""
import unittest
from datetime import date

from modules.elm.domain.rules import (
    can_cancel,
    can_withdraw,
    overlaps,
    validate_substitute,
)


class OverlapTests(unittest.TestCase):
    # BR-EL-012
    def test_disjoint_ranges_do_not_overlap(self):
        self.assertFalse(overlaps(
            date(2026, 1, 1), date(2026, 1, 2), "none",
            date(2026, 1, 5), date(2026, 1, 6), "none",
        ))

    def test_identical_full_day_ranges_overlap(self):
        self.assertTrue(overlaps(
            date(2026, 1, 1), date(2026, 1, 1), "none",
            date(2026, 1, 1), date(2026, 1, 1), "none",
        ))

    def test_first_and_second_half_same_day_do_not_overlap(self):
        self.assertFalse(overlaps(
            date(2026, 1, 1), date(2026, 1, 1), "first_half",
            date(2026, 1, 1), date(2026, 1, 1), "second_half",
        ))
        self.assertFalse(overlaps(  # order-independent
            date(2026, 1, 1), date(2026, 1, 1), "second_half",
            date(2026, 1, 1), date(2026, 1, 1), "first_half",
        ))

    def test_same_half_same_day_overlaps(self):
        self.assertTrue(overlaps(
            date(2026, 1, 1), date(2026, 1, 1), "first_half",
            date(2026, 1, 1), date(2026, 1, 1), "first_half",
        ))

    def test_half_day_exception_does_not_apply_to_multi_day_ranges(self):
        self.assertTrue(overlaps(
            date(2026, 1, 1), date(2026, 1, 3), "first_half",
            date(2026, 1, 1), date(2026, 1, 3), "second_half",
        ))

    def test_adjacent_but_touching_ranges_overlap(self):
        self.assertTrue(overlaps(
            date(2026, 1, 1), date(2026, 1, 5), "none",
            date(2026, 1, 5), date(2026, 1, 8), "none",
        ))


class SubstituteTests(unittest.TestCase):
    # BR-EL-014
    def test_no_substitute_required(self):
        self.assertEqual(validate_substitute(1, None, True, False), (True, "not required"))

    def test_substitute_cannot_be_applicant(self):
        ok, _ = validate_substitute(1, 1, True, False)
        self.assertFalse(ok)

    def test_substitute_must_be_known_employee(self):
        ok, _ = validate_substitute(1, 2, False, False)
        self.assertFalse(ok)

    def test_substitute_cannot_have_conflicting_leave(self):
        ok, _ = validate_substitute(1, 2, True, True)
        self.assertFalse(ok)

    def test_eligible_substitute_accepted(self):
        self.assertEqual(validate_substitute(1, 2, True, False), (True, "eligible"))


class LifecycleTests(unittest.TestCase):
    # BR-EL-022 / BR-EL-034
    def test_can_withdraw_only_when_pending(self):
        self.assertTrue(can_withdraw("pending"))
        for s in ("approved", "rejected", "withdrawn", "cancelled",
                  "unit_head_recommended", "unit_head_not_recommended"):
            self.assertFalse(can_withdraw(s), f"status={s}")

    # BR-EL-023
    def test_can_cancel_only_when_approved_and_before_start(self):
        self.assertTrue(can_cancel("approved", date(2026, 6, 1), date(2026, 5, 1)))

    def test_cannot_cancel_on_or_after_start_date(self):
        self.assertFalse(can_cancel("approved", date(2026, 6, 1), date(2026, 6, 1)))
        self.assertFalse(can_cancel("approved", date(2026, 6, 1), date(2026, 6, 2)))

    def test_cannot_cancel_non_approved(self):
        self.assertFalse(can_cancel("pending", date(2026, 6, 1), date(2026, 5, 1)))


if __name__ == "__main__":
    unittest.main()
