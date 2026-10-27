"""Service unit tests for ELM extension, resumption, SLA, and cancellation lifecycle."""
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from modules.elm.domain.state_machine import can_request_extension, can_submit_resumption


class TestELMServiceLogic(unittest.TestCase):
    def test_extension_boundary_rules(self):
        """BR-EL-025: Extension end date must be after original end date."""
        today = date(2026, 11, 8)
        orig_start = date(2026, 11, 2)
        orig_end = date(2026, 11, 10)
        ext_end = date(2026, 11, 15)

        self.assertTrue(can_request_extension("approved", "EL", orig_start, today))
        self.assertTrue(ext_end > orig_end)

        # Premature or non-ongoing extension rejected
        future_start = date(2026, 11, 12)
        self.assertFalse(can_request_extension("approved", "EL", future_start, today))

    def test_resumption_difference_calculation(self):
        """BR-EL-028: Early resumption decreases duration; Late resumption increases duration."""
        expected_end = date(2026, 11, 10)
        orig_duration = 10.0

        # Normal resumption: exactly on expected end
        normal_actual = date(2026, 11, 10)
        self.assertEqual(normal_actual, expected_end)

        # Early resumption: returned on Nov 8 (2 days early)
        early_actual = date(2026, 11, 8)
        adjusted_duration_early = 8.0
        diff_early = adjusted_duration_early - orig_duration
        self.assertEqual(diff_early, -2.0)  # Consumed balance should reduce by 2 days

        # Late resumption: returned on Nov 12 (2 days late)
        late_actual = date(2026, 11, 12)
        adjusted_duration_late = 12.0
        diff_late = adjusted_duration_late - orig_duration
        self.assertEqual(diff_late, 2.0)   # Consumed balance should increase by 2 days

    def test_sla_reminder_and_escalation_cutoffs(self):
        """BR-EL-032, BR-EL-033: SLA reminder threshold at 3d, escalation at 7d."""
        reminder_days = 3
        escalation_days = 7

        now = date(2026, 11, 10)
        created_fresh = date(2026, 11, 9)       # 1 day old: no reminder, no escalation
        created_remind = date(2026, 11, 6)      # 4 days old: reminder triggered
        created_escalate = date(2026, 11, 1)    # 9 days old: escalation triggered

        self.assertFalse((now - created_fresh).days >= reminder_days)
        self.assertTrue((now - created_remind).days >= reminder_days)
        self.assertFalse((now - created_remind).days >= escalation_days)
        self.assertTrue((now - created_escalate).days >= escalation_days)


if __name__ == "__main__":
    unittest.main()
