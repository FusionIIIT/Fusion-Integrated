from datetime import date
from unittest.mock import patch

from django.test import TestCase

from modules.directory.contracts import UserDTO
from modules.elm.models import (
    HierarchyRule,
    HolidayCalendar,
    LeaveAccount,
    LeavePolicy,
    WorkflowTask,
)
from modules.elm.services import accounts, policy, validation
from modules.elm.services import applications as app
from modules.elm.services import lifecycle as life

MON = date(2026, 11, 2)
TUE = date(2026, 11, 3)
FRI = date(2026, 11, 6)
USERS = {i: UserDTO(user_id=i, username=f"u{i}", display_name=f"U{i}",
                    kind="staff", department="CSE") for i in (1, 2, 3, 10, 20, 40)}


class Base(TestCase):
    def setUp(self):
        p = patch("modules.elm.services.applications.get_users",
                  side_effect=lambda ids: {i: USERS[i] for i in ids if i in USERS})
        p.start()
        self.addCleanup(p.stop)
        policy.publish_policy(LeavePolicy.objects.create(version=1, params=policy.DEFAULT_PARAMS))
        policy.publish_calendar(HolidayCalendar.objects.create(year=2026, version=1))
        for uid in (1, 2, 3):
            accounts.credit_annual(uid, 2026, "staff", policy.DEFAULT_PARAMS)
        for stage, who in (("unit_head", 10), ("final", 40)):
            HierarchyRule.objects.create(stage=stage, approver_id=who, status="published")

    def bal(self, leave_type, uid=1):
        return LeaveAccount.objects.get(user_id=uid, year=2026, leave_type=leave_type).balance

    def approved_el(self):
        r = app.submit(app.create_draft(1, "EL", MON, FRI, "rest").pk)
        app.unit_head_decide(r.pk, 10, "recommended")
        return app.final_decide(r.pk, 40, "approved")

    def approved_cl(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        return app.unit_head_decide(r.pk, 10, "approved")


class ModifyTests(Base):
    def test_modify_reroutes_and_supersedes(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        r = life.modify(r.pk, 1, start_date=TUE, end_date=TUE)
        self.assertEqual(r.status, "awaiting_unit_head")
        self.assertEqual(r.start_date, TUE)
        self.assertEqual(WorkflowTask.objects.filter(request=r, status="superseded").count(), 1)
        self.assertEqual(WorkflowTask.objects.filter(request=r, status="open").count(), 1)

    def test_invalid_modification_changes_nothing(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        with self.assertRaises(validation.LeaveValidationError):
            life.modify(r.pk, 1, end_date=date(2026, 11, 20))
        r.refresh_from_db()
        self.assertEqual(r.end_date, MON)
        self.assertEqual(WorkflowTask.objects.filter(request=r, status="open").count(), 1)

    def test_modify_after_approval_refused(self):
        r = self.approved_cl()
        with self.assertRaises(app.ApplicationError):
            life.modify(r.pk, 1, reason="changed")

    def test_modify_requires_fresh_substitute_consent(self):
        d = app.create_draft(1, "EL", MON, FRI, "rest", substitute_required=True)
        r = app.submit(d.pk, nominee_id=2)
        r = app.respond_substitute(r.pk, 2, accept=True)
        self.assertEqual(r.status, "awaiting_unit_head")
        r = life.modify(r.pk, 1, nominee_id=3, reason="new reason")
        self.assertEqual(r.status, "awaiting_substitute")
        r = app.respond_substitute(r.pk, 3, accept=True)
        self.assertEqual(r.status, "awaiting_unit_head")


class CancelTests(Base):
    TODAY = date(2026, 10, 30)

    def test_cancel_approved_el_through_hierarchy(self):
        parent = self.approved_el()
        self.assertEqual(self.bal("EL"), 25)
        c = life.request_cancellation(parent.pk, 1, today=self.TODAY)
        parent.refresh_from_db()
        self.assertEqual(parent.status, "cancellation_pending")
        app.unit_head_decide(c.pk, 10, "recommended")
        app.final_decide(c.pk, 40, "approved")
        parent.refresh_from_db()
        self.assertEqual(parent.status, "cancelled")
        self.assertEqual(self.bal("EL"), 30)

    def test_cancel_cl_decided_by_unit_head(self):
        parent = self.approved_cl()
        c = life.request_cancellation(parent.pk, 1, today=self.TODAY)
        app.unit_head_decide(c.pk, 10, "approved")
        parent.refresh_from_db()
        self.assertEqual(parent.status, "cancelled")
        self.assertEqual(self.bal("CL"), 8)

    def test_rejected_cancellation_preserves_leave(self):
        parent = self.approved_el()
        c = life.request_cancellation(parent.pk, 1, today=self.TODAY)
        app.unit_head_decide(c.pk, 10, "recommended")
        app.final_decide(c.pk, 40, "rejected")
        parent.refresh_from_db()
        self.assertEqual(parent.status, "approved")
        self.assertEqual(self.bal("EL"), 25)

    def test_withdrawn_cancellation_preserves_leave(self):
        parent = self.approved_el()
        c = life.request_cancellation(parent.pk, 1, today=self.TODAY)
        app.withdraw(c.pk, 1)
        parent.refresh_from_db()
        self.assertEqual(parent.status, "approved")

    def test_cannot_cancel_after_start(self):
        parent = self.approved_el()
        with self.assertRaises(app.ApplicationError):
            life.request_cancellation(parent.pk, 1, today=MON)

    def test_cannot_cancel_unapproved(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        with self.assertRaises(app.ApplicationError):
            life.request_cancellation(r.pk, 1, today=self.TODAY)


class ExtendTests(Base):
    TODAY = date(2026, 11, 4)

    def test_approved_extension_posts_only_the_increment(self):
        parent = self.approved_el()
        c = life.extend(parent.pk, 1, date(2026, 11, 9), today=self.TODAY)
        self.assertEqual(c.days, 3)
        self.assertEqual(c.status, "awaiting_unit_head")
        app.unit_head_decide(c.pk, 10, "recommended")
        app.final_decide(c.pk, 40, "approved")
        parent.refresh_from_db()
        self.assertEqual(self.bal("EL"), 22)
        self.assertEqual(parent.end_date, date(2026, 11, 9))
        self.assertEqual(parent.days, 8)

    def test_rejected_extension_leaves_original_unchanged(self):
        parent = self.approved_el()
        c = life.extend(parent.pk, 1, date(2026, 11, 9), today=self.TODAY)
        app.unit_head_decide(c.pk, 10, "not_recommended")
        app.final_decide(c.pk, 40, "rejected")
        parent.refresh_from_db()
        self.assertEqual(self.bal("EL"), 25)
        self.assertEqual(parent.end_date, FRI)

    def test_extension_not_defined_for_cl(self):
        parent = self.approved_cl()
        with self.assertRaises(app.ApplicationError):
            life.extend(parent.pk, 1, TUE, today=MON)

    def test_only_ongoing_leave_can_be_extended(self):
        parent = self.approved_el()
        with self.assertRaises(app.ApplicationError):
            life.extend(parent.pk, 1, date(2026, 11, 9), today=date(2026, 10, 30))


class ResumptionTests(Base):
    def test_early_resumption_restores_unused_after_verification(self):
        parent = self.approved_el()                     # 5 days, balance 25
        life.submit_resumption(parent.pk, 1, date(2026, 11, 4), today=date(2026, 11, 4))
        parent.refresh_from_db()
        self.assertEqual(parent.status, "awaiting_resumption")
        self.assertEqual(self.bal("EL"), 25)            # nothing restored before verification
        life.verify_resumption(parent.pk, 10)
        parent.refresh_from_db()
        self.assertEqual(parent.status, "closed")
        self.assertEqual(self.bal("EL"), 28)            # 4 Nov, 5 Nov, 6 Nov unused

    def test_normal_return_restores_nothing(self):
        parent = self.approved_el()
        life.submit_resumption(parent.pk, 1, date(2026, 11, 7), today=date(2026, 11, 7))
        life.verify_resumption(parent.pk, 10)
        parent.refresh_from_db()
        self.assertEqual(parent.status, "closed")
        self.assertEqual(self.bal("EL"), 25)

    def test_unverified_return_stays_open(self):
        parent = self.approved_el()
        life.submit_resumption(parent.pk, 1, date(2026, 11, 4), today=date(2026, 11, 4))
        life.verify_resumption(parent.pk, 10, verified=False)
        parent.refresh_from_db()
        self.assertEqual(parent.status, "awaiting_resumption")
        self.assertEqual(self.bal("EL"), 25)
        self.assertTrue(WorkflowTask.objects.filter(
            request=parent, stage="verify_resumption", status="open").exists())

    def test_only_the_verifier_can_verify(self):
        parent = self.approved_el()
        life.submit_resumption(parent.pk, 1, date(2026, 11, 4), today=date(2026, 11, 4))
        with self.assertRaises(app.ApplicationError):
            life.verify_resumption(parent.pk, 99)

    def test_resumption_not_defined_for_cl(self):
        parent = self.approved_cl()
        with self.assertRaises(app.ApplicationError):
            life.submit_resumption(parent.pk, 1, MON, today=MON)
