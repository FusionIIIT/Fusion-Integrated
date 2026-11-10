"""Tests for BADMS domain rules and state machine (no DB required)."""
import unittest
from modules.badms.domain import state_machine as sm


class BadmsDomainTestCase(unittest.TestCase):
    def test_hod_approval_and_rejection(self):
        self.assertEqual(sm.validate_hod_decision("approve"), sm.ARCHIVAL_HOD_APPROVED)
        self.assertEqual(sm.validate_hod_decision("reject"), sm.ARCHIVAL_HOD_REJECTED)
        with self.assertRaises(sm.InvalidTransition):
            sm.validate_hod_decision("invalid")

    def test_storage_quota_threshold(self):
        # If usage is below quota, extension cannot be requested (BR-BA-016)
        with self.assertRaises(sm.RuleViolation):
            sm.validate_storage_quota_threshold(current_usage_mb=4000, quota_mb=5120)

        # When usage meets or exceeds quota, validation succeeds
        sm.validate_storage_quota_threshold(current_usage_mb=5120, quota_mb=5120)
        sm.validate_storage_quota_threshold(current_usage_mb=5200, quota_mb=5120)

    def test_local_schedule_overrides_global(self):
        # BR-BA-011: Local schedule takes precedence over global
        global_sch = {"cron": "0 0 * * *", "scope": "global"}
        local_sch = {"cron": "0 3 * * *", "scope": "local"}
        schedules = {"finance_db": local_sch}

        eff = sm.calculate_effective_schedule("finance_db", schedules, global_sch)
        self.assertEqual(eff, local_sch)

        eff_default = sm.calculate_effective_schedule("unknown_db", schedules, global_sch)
        self.assertEqual(eff_default, global_sch)

    def test_repeated_failure_escalation(self):
        # BR-BA-015: 3 consecutive failures trigger escalation
        self.assertFalse(sm.check_repeated_failure_escalation(2))
        self.assertTrue(sm.check_repeated_failure_escalation(3))
        self.assertTrue(sm.check_repeated_failure_escalation(4))

    def test_retention_years(self):
        # BR-BA-008: Tier retention definitions
        self.assertEqual(sm.RETENTION_YEARS[sm.TIER_ROUTINE], 1)
        self.assertEqual(sm.RETENTION_YEARS[sm.TIER_ARCHIVAL], 5)
        self.assertEqual(sm.RETENTION_YEARS[sm.TIER_SENSITIVE], 7)
        self.assertEqual(sm.RETENTION_YEARS[sm.TIER_CRITICAL], 10)


if __name__ == "__main__":
    unittest.main()
