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

    def test_no_duplicate_pending_extension(self):
        # BR-BA-009: cannot submit a new request when one is already pending
        with self.assertRaises(sm.RuleViolation) as ctx:
            sm.validate_no_pending_extension(pending_count=1)
        self.assertEqual(ctx.exception.rule_id, "BR-BA-009")

        # zero pending — should pass
        sm.validate_no_pending_extension(pending_count=0)

    def test_invalid_hod_action_raises(self):
        # Any action other than 'approve'/'reject' should raise InvalidTransition
        with self.assertRaises(sm.InvalidTransition):
            sm.validate_hod_decision("pending")
        with self.assertRaises(sm.InvalidTransition):
            sm.validate_hod_decision("")

    def test_all_tiers_have_retention(self):
        # Every tier in ALL_TIERS must have a defined retention year
        for tier in sm.ALL_TIERS:
            self.assertIn(tier, sm.RETENTION_YEARS)
            self.assertGreater(sm.RETENTION_YEARS[tier], 0)


if __name__ == "__main__":
    unittest.main()

