from datetime import date

from django.test import TestCase

from modules.elm.models import HolidayCalendar, LeavePolicy, PublishState
from modules.elm.services import policy


class PolicyTests(TestCase):
    def test_no_policy_raises(self):
        with self.assertRaises(policy.NoPublishedPolicy):
            policy.get_effective_policy()

    def test_publish_retires_previous(self):
        p1 = LeavePolicy.objects.create(version=1, params=policy.DEFAULT_PARAMS)
        policy.publish_policy(p1)
        p2 = LeavePolicy.objects.create(version=2, params=policy.DEFAULT_PARAMS)
        policy.publish_policy(p2)
        p1.refresh_from_db()
        self.assertEqual(p1.status, PublishState.RETIRED)
        self.assertEqual(policy.get_effective_policy().version, 2)

    def test_invalid_publish_keeps_old_policy_in_force(self):
        p1 = LeavePolicy.objects.create(version=1, params=policy.DEFAULT_PARAMS)
        policy.publish_policy(p1)
        bad = LeavePolicy.objects.create(version=2, params={"CL": -1})
        with self.assertRaises(policy.PolicyError):
            policy.publish_policy(bad)
        self.assertEqual(policy.get_effective_policy().version, 1)

    def test_future_effective_date_not_used_yet(self):
        p1 = LeavePolicy.objects.create(version=1, params=policy.DEFAULT_PARAMS)
        policy.publish_policy(p1)
        future = LeavePolicy.objects.create(
            version=2, params=policy.DEFAULT_PARAMS, effective_from=date(2999, 1, 1))
        policy.publish_policy(future)
        # publishing retires v1, so with only a future policy nothing is in force
                # v1 stays in force until v2's effective date (SRS-EL-091)
        self.assertEqual(policy.get_effective_policy(date(2026, 10, 25)).version, 1)
        self.assertEqual(policy.get_effective_policy(date(3000, 1, 1)).version, 2)

    def test_calendar_publish_and_lookup(self):
        c1 = HolidayCalendar.objects.create(year=2026, version=1)
        policy.publish_calendar(c1)
        self.assertEqual(policy.get_effective_calendar(2026).pk, c1.pk)
        with self.assertRaises(policy.NoPublishedCalendar):
            policy.get_effective_calendar(2027)
