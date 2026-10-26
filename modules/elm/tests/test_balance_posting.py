from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveLedgerEntry, LeavePolicy
from modules.elm.services import post_application_balance


class LeaveBalancePostingTests(TestCase):
    def setUp(self):
        LeavePolicy.objects.update_or_create(
            category="CL",
            defaults={
                "annual_entitlement": Decimal("8.00"),
                "employee_scope": "all",
                "carry_forward": False,
                "continuous_counting": False,
                "medical_evidence_required": False,
                "enabled": True,
            },
        )

    def make_application(self, *, request_type="leave", requested_days="3.00", user_id=101):
        return LeaveApplication.objects.create(
            applicant_user_id=user_id,
            employee_kind="staff",
            department="Computer Science",
            request_type=request_type,
            category="CL",
            start_date=date(2026, 10, 12),
            end_date=date(2026, 10, 14),
            requested_days=Decimal(requested_days),
            requested_days_by_year={"2026": requested_days},
            purpose="Test posting balance",
            status="approved",
            final_decision="approved",
            evidence_reference="OFFLINE-TEST" if request_type == "offline" else "",
        )

    def test_normal_approval_does_not_overdraw_balance(self):
        LeaveBalance.objects.create(
            user_id=101,
            employee_kind="staff",
            year=2026,
            category="CL",
            entitlement=Decimal("2.00"),
        )
        app = self.make_application(requested_days="3.00")

        with self.assertRaises(ValidationError):
            post_application_balance(app, actor_user_id=500)

        balance = LeaveBalance.objects.get(user_id=101, year=2026, category="CL")
        self.assertEqual(balance.consumed, Decimal("0.00"))
        self.assertFalse(LeaveLedgerEntry.objects.filter(application=app).exists())

    def test_historical_offline_sanction_can_reconcile_overspent_balance(self):
        app = self.make_application(request_type="offline", requested_days="10.00", user_id=202)

        post_application_balance(app, actor_user_id=500)

        balance = LeaveBalance.objects.get(user_id=202, year=2026, category="CL")
        self.assertEqual(balance.consumed, Decimal("10.00"))
        self.assertEqual(balance.available, Decimal("-2.00"))
        self.assertTrue(LeaveLedgerEntry.objects.filter(application=app).exists())
