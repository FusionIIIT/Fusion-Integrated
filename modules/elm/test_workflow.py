
from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeavePolicy, LeaveRequest, LeaveAccount
from modules.elm.services.workflow import submit, transition


class LeaveWorkflowTests(TestCase):

    def setUp(self):
        self.actor = SimpleNamespace(user_id=101)
        self.start = timezone.localdate() + timedelta(days=2)

    def make_policy(self, entitlement=10):
        return LeavePolicy.objects.create(
            category="EL",
            annual_entitlement=entitlement,
            requires_substitute=False,
            higher_sanction=False,
            enabled=True,
        )

    def make_application(self, start=None, days=3):
        start = start or self.start
        return {
            "category": "EL",
            "start_date": start,
            "end_date": start + timedelta(days=days - 1),
            "purpose": "Personal work",
            "station_leave": {},
        }

    def test_application_is_created(self):
        self.make_policy()

        request = submit(
            actor=self.actor,
            data=self.make_application(),
        )

        self.assertEqual(
            request.status,
            "awaiting_unit_head_review",
        )
        self.assertEqual(request.days, 3)

    def test_pending_requests_cannot_exceed_balance(self):
        self.make_policy(entitlement=10)

        submit(
            actor=self.actor,
            data=self.make_application(days=6),
        )

        with self.assertRaises(ValidationError):
            submit(
                actor=self.actor,
                data=self.make_application(
                    start=self.start + timedelta(days=10),
                    days=5,
                ),
            )

    def test_approval_deducts_balance(self):
        self.make_policy(entitlement=10)

        request = submit(
            actor=self.actor,
            data=self.make_application(days=3),
        )

        transition(
            request_obj=request,
            actor=self.actor,
            action="approve",
        )

        account = LeaveAccount.objects.get(
            user_id=self.actor.user_id,
            category="EL",
            year=self.start.year,
        )

        self.assertEqual(account.balance, 7)
        self.assertEqual(
            LeaveRequest.objects.get(pk=request.pk).status,
            "approved",
        )
