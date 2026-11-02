
"""Tests for MMS services and business logic."""

from datetime import date, timedelta
import pytest
from django.test import TestCase

from modules.mms import services
from modules.mms.models import MessRegistration, MessRoleAssignment, RebateRequest, RegistrationWindow


@pytest.mark.django_db
class MMSServiceTests(TestCase):
    def setUp(self):
        self.today = date.today()
        self.window = services.open_registration_window(
            semester="Monsoon 2026",
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=10),
            created_by_id=1,
        )

    def test_assign_role_and_single_active_role(self):
        # Assign caretaker 1
        c1 = services.assign_mess_role("Mess 1", "caretaker", employee_id=101, assigned_by_id=1)
        self.assertTrue(c1.is_active)

        # Assign caretaker 2 -> caretaker 1 becomes inactive (BR-MMS-003)
        c2 = services.assign_mess_role("Mess 1", "caretaker", employee_id=102, assigned_by_id=1)
        self.assertTrue(c2.is_active)
        c1.refresh_from_db()
        self.assertFalse(c1.is_active)

    def test_registration_flow(self):
        reg = services.submit_registration(student_id=201, mess_name="Mess 1", window_id=self.window.id)
        self.assertEqual(reg.status, "PENDING")

        # Review
        approved = services.review_registration(reg.id, reviewer_id=102, approve=True)
        self.assertEqual(approved.status, "REGISTERED")

    def test_rebate_flow(self):
        start = self.today + timedelta(days=2)
        end = self.today + timedelta(days=6)
        rebate = services.submit_rebate_request(
            student_id=201,
            mess_name="Mess 1",
            start_date=start,
            end_date=end,
            reason="Going home",
        )
        self.assertEqual(rebate.duration_days, 4)

        # Overlap check
        with pytest.raises(ValueError):
            services.submit_rebate_request(
                student_id=201,
                mess_name="Mess 1",
                start_date=start + timedelta(days=1),
                end_date=end + timedelta(days=2),
                reason="Overlap",
            )
