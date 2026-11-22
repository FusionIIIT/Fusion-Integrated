from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from modules.elm.models import LeaveApplication, LeaveHierarchy
from modules.elm.services import retry_after_substitute_decline


class SubstituteRetryTests(TestCase):
    def test_applicant_can_continue_without_replacement_substitute(self):
        LeaveHierarchy.objects.create(
            unit_key="Computer Science",
            unit_head_user_id=202,
            establishment_user_id=None,
            sanctioning_authority_user_id=None,
            director_user_id=None,
            active=True,
        )
        app = LeaveApplication.objects.create(
            applicant_user_id=101,
            employee_kind="staff",
            department="Computer Science",
            request_type="leave",
            category="CL",
            start_date=date(2026, 10, 19),
            end_date=date(2026, 10, 19),
            requested_days=Decimal("1.00"),
            requested_days_by_year={"2026": "1.00"},
            purpose="Test substitute retry",
            requires_substitute=True,
            substitute_user_id=303,
            substitute_response="declined",
            status="action_required",
            current_assignee_user_id=101,
        )

        updated = retry_after_substitute_decline(
            SimpleNamespace(user_id=101),
            app,
            substitute_user_id=None,
        )

        self.assertEqual(updated.status, "awaiting_unit_head")
        self.assertEqual(updated.current_assignee_user_id, 202)
        self.assertFalse(updated.requires_substitute)
        self.assertIsNone(updated.substitute_user_id)
        self.assertEqual(updated.substitute_response, "not_required")
