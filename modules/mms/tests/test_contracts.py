"""Tests for MMS cross-module contracts (ADR-0004)."""

from datetime import date
import pytest
from django.test import TestCase

from modules.mms import contracts
from modules.mms.models import MessRegistration, MessRoleAssignment, RebateRequest, RegistrationWindow


@pytest.mark.django_db
class MMSContractsTests(TestCase):
    def setUp(self):
        self.window = RegistrationWindow.objects.create(
            semester="Monsoon 2026",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 1),
            is_open=True,
            created_by_id=1,
        )
        self.reg = MessRegistration.objects.create(
            student_id=501,
            mess_name="Central Mess",
            window=self.window,
            status="REGISTERED",
        )
        self.rebate = RebateRequest.objects.create(
            student_id=501,
            mess_name="Central Mess",
            start_date=date(2026, 9, 10),
            end_date=date(2026, 9, 15),
            duration_days=6,
            status="APPROVED",
        )
        self.role = MessRoleAssignment.objects.create(
            mess_name="Central Mess",
            role="caretaker",
            employee_id=301,
            is_active=True,
        )

    def test_get_student_mess_registrations(self):
        res = contracts.get_student_mess_registrations([501, 999])
        self.assertIn("results", res)
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["student_id"], 501)
        self.assertEqual(res["results"][0]["mess_name"], "Central Mess")

    def test_get_student_approved_rebates(self):
        res = contracts.get_student_approved_rebates([501])
        self.assertIn("results", res)
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["duration_days"], 6)

    def test_get_active_mess_roles(self):
        res = contracts.get_active_mess_roles([301, 999])
        self.assertIn("results", res)
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["role"], "caretaker")

