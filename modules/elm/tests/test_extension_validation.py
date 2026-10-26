from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeaveApplication, LeaveHierarchy, LeavePolicy, VacationPeriod
from modules.elm.services import create_extension


class LeaveExtensionValidationTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        days_until_friday = (4 - self.today.weekday()) % 7
        self.parent_end = self.today + timedelta(days=days_until_friday)

        LeaveHierarchy.objects.update_or_create(
            unit_key="Computer Science",
            defaults={
                "unit_head_user_id": 201,
                "establishment_user_id": 202,
                "sanctioning_authority_user_id": 203,
                "director_user_id": 204,
                "active": True,
            },
        )

    def configure_policy(
        self,
        category,
        *,
        employee_scope,
        enabled=True,
        continuous_counting=True,
    ):
        LeavePolicy.objects.update_or_create(
            category=category,
            defaults={
                "annual_entitlement": Decimal("60.00" if category == "VL" else "30.00"),
                "employee_scope": employee_scope,
                "carry_forward": category in {"EL", "COL"},
                "continuous_counting": continuous_counting,
                "medical_evidence_required": False,
                "enabled": enabled,
            },
        )

    def make_parent(self, category, employee_kind):
        start = self.today - timedelta(days=1)
        years = {str(year): "1.00" for year in range(start.year, self.parent_end.year + 1)}
        return LeaveApplication.objects.create(
            applicant_user_id=101,
            employee_kind=employee_kind,
            department="Computer Science",
            request_type="leave",
            category=category,
            start_date=start,
            end_date=self.parent_end,
            requested_days=Decimal("1.00"),
            requested_days_by_year=years,
            purpose="Assignment 6-B extension validation test",
            status="approved",
            final_decision="approved",
        )

    def request_extension(self, parent, start=None, end=None):
        start = start or parent.end_date + timedelta(days=1)
        end = end or start + timedelta(days=1)
        actor = type("Actor", (), {"user_id": parent.applicant_user_id})()
        return create_extension(
            actor=actor,
            parent=parent,
            start=start,
            end=end,
            reason="Regression test",
        )

    def test_extension_rejects_disabled_leave_policy(self):
        self.configure_policy("EL", employee_scope="staff", enabled=False)
        parent = self.make_parent("EL", "staff")

        with self.assertRaises(ValidationError):
            self.request_extension(parent)

        self.assertFalse(LeaveApplication.objects.filter(parent_application=parent).exists())

    def test_extension_rejects_employee_kind_outside_current_policy_scope(self):
        self.configure_policy("EL", employee_scope="faculty", enabled=True)
        parent = self.make_parent("EL", "staff")

        with self.assertRaises(ValidationError):
            self.request_extension(parent)

        self.assertFalse(LeaveApplication.objects.filter(parent_application=parent).exists())

    def test_vacation_leave_extension_must_remain_inside_active_vacation_period(self):
        self.configure_policy("VL", employee_scope="faculty")
        parent = self.make_parent("VL", "faculty")
        VacationPeriod.objects.create(
            name="Parent leave only",
            start_date=parent.start_date,
            end_date=parent.end_date,
            active=True,
        )

        with self.assertRaises(ValidationError):
            self.request_extension(parent)

        self.assertFalse(LeaveApplication.objects.filter(parent_application=parent).exists())

    def test_extension_with_no_countable_days_is_rejected(self):
        self.configure_policy("EL", employee_scope="staff", continuous_counting=False)
        parent = self.make_parent("EL", "staff")
        saturday = parent.end_date + timedelta(days=1)
        # The parent ends on Friday; this extension covers Saturday and Sunday.
        self.assertEqual(saturday.weekday(), 5)

        with self.assertRaises(ValidationError):
            self.request_extension(parent, saturday, saturday + timedelta(days=1))

        self.assertFalse(LeaveApplication.objects.filter(parent_application=parent).exists())
