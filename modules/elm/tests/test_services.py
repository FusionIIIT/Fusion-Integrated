"""Django-ORM-level integration tests for the service layer. Requires a real
database to run (`manage.py test`, normally against this project's Postgres).

Verification note (Phase 2, Assignment 6B): these exact scenarios were run
and PASSED via a one-off script against `migrate elm` + `migrate directory`
on a local SQLite substitute (no Postgres available in this environment —
see UNRESOLVED.md). `manage.py test` itself could NOT be run here because
Django's test runner migrates every installed app for the test database,
and an existing modules/placement migration is Postgres-specific and fails
under SQLite (unrelated to ELM; not something this phase touches). This
file should be re-run against the project's real Postgres (e.g. in CI or
`make up && make test`) for the authoritative result.
"""
from datetime import date, timedelta

from django.test import TestCase

from core.api.exceptions import BadRequestError, ConflictError
from modules.directory.models import UserRef
from modules.elm.services import leave_requests as svc


class LeaveLifecycleTests(TestCase):
    def setUp(self):
        self.applicant_id = 101
        self.unit_head_id = 999
        self.substitute_id = 102
        UserRef.objects.create(user_id=self.applicant_id, username="alice",
                               display_name="Alice", kind="staff", is_active=True)
        UserRef.objects.create(user_id=self.substitute_id, username="bob",
                               display_name="Bob", kind="staff", is_active=True)
        self.start = date.today() + timedelta(days=5)
        self.end = self.start

    def test_submit_then_unit_head_approves_cl(self):
        row = svc.submit(
            applicant_user_id=self.applicant_id, category="CL",
            start_date=self.start, end_date=self.end,
            unit_head_user_id=self.unit_head_id,
            substitute_user_id=self.substitute_id, reason="personal",
        )
        self.assertEqual(row.status, "pending")
        self.assertEqual(row.substitute_consent, "pending")  # BR-EL-015

        decided = svc.decide_as_unit_head(
            acting_user_id=self.unit_head_id, leave_request_id=row.pk,
            approve=True, remarks="ok",
        )
        self.assertEqual(decided.status, "approved")  # BR-EL-016

    def test_overlapping_request_rejected(self):
        svc.submit(applicant_user_id=self.applicant_id, category="CL",
                  start_date=self.start, end_date=self.end,
                  unit_head_user_id=self.unit_head_id)
        with self.assertRaises(ConflictError):  # BR-EL-012
            svc.submit(applicant_user_id=self.applicant_id, category="CL",
                      start_date=self.start, end_date=self.end,
                      unit_head_user_id=self.unit_head_id)

    def test_withdraw_blocked_after_approval(self):
        row = svc.submit(applicant_user_id=self.applicant_id, category="CL",
                         start_date=self.start, end_date=self.end,
                         unit_head_user_id=self.unit_head_id)
        svc.decide_as_unit_head(acting_user_id=self.unit_head_id,
                                leave_request_id=row.pk, approve=True)
        with self.assertRaises(ConflictError):  # BR-EL-022/034
            svc.withdraw(acting_user_id=self.applicant_id, leave_request_id=row.pk)

    def test_cancel_approved_future_leave(self):
        row = svc.submit(applicant_user_id=self.applicant_id, category="CL",
                         start_date=self.start, end_date=self.end,
                         unit_head_user_id=self.unit_head_id)
        svc.decide_as_unit_head(acting_user_id=self.unit_head_id,
                                leave_request_id=row.pk, approve=True)
        cancelled = svc.cancel(acting_user_id=self.applicant_id,
                               leave_request_id=row.pk)
        self.assertEqual(cancelled.status, "cancelled")  # BR-EL-023

    def test_substitute_cannot_be_applicant(self):
        with self.assertRaises(BadRequestError):  # BR-EL-014
            svc.submit(applicant_user_id=self.applicant_id, category="CL",
                      start_date=self.start, end_date=self.end,
                      unit_head_user_id=self.unit_head_id,
                      substitute_user_id=self.applicant_id)

    def test_unknown_substitute_rejected(self):
        with self.assertRaises(BadRequestError):  # BR-EL-014
            svc.submit(applicant_user_id=self.applicant_id, category="CL",
                      start_date=self.start, end_date=self.end,
                      unit_head_user_id=self.unit_head_id,
                      substitute_user_id=999999)
