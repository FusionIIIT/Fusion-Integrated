from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone

from modules.directory.contracts import UserDTO
from modules.elm.models import (
    HierarchyRule,
    HolidayCalendar,
    LeaveAccount,
    LeavePolicy,
    LeaveRequest,
    LeaveTransaction,
    OfflineRecord,
    SlaLog,
    WorkflowTask,
)
from modules.elm.services import accounts, offline, policy, validation
from modules.elm.services import applications as app
from modules.elm.services import scheduled as sched

MON = date(2026, 11, 2)
FRI = date(2026, 11, 6)
USERS = {i: UserDTO(user_id=i, username=f"u{i}", display_name=f"U{i}",
                    kind="staff", department="CSE") for i in (1, 2, 3, 7, 10, 20, 40)}


class JobsBase(TestCase):
    def setUp(self):
        p = patch("modules.elm.services.applications.get_users",
                  side_effect=lambda ids: {i: USERS[i] for i in ids if i in USERS})
        p.start()
        self.addCleanup(p.stop)
        policy.publish_policy(LeavePolicy.objects.create(version=1, params=policy.DEFAULT_PARAMS))
        policy.publish_calendar(HolidayCalendar.objects.create(year=2026, version=1))
        for stage, who in (("unit_head", 10), ("final", 40), ("director", 7)):
            HierarchyRule.objects.create(stage=stage, approver_id=who, status="published")

    def bal(self, uid, year, leave_type):
        return LeaveAccount.objects.get(user_id=uid, year=year, leave_type=leave_type).balance


class OfflineTests(JobsBase):
    def setUp(self):
        super().setUp()
        accounts.credit_annual(1, 2026, "staff", policy.DEFAULT_PARAMS)

    def rec(self, **kw):
        args = {"admin_id": 20, "applicant_id": 1, "leave_type": "EL", "start": MON, "end": FRI,
                    "reference": "Office Order 12/2026", "sanctioned_by": "Registrar",
                    "sanctioned_on": date(2026, 10, 1)}
        args.update(kw)
        return offline.record_offline(**args)

    def test_records_approved_leave_and_updates_balance(self):
        r = self.rec()
        self.assertEqual(r.status, "approved")
        self.assertEqual(self.bal(1, 2026, "EL"), 25)
        self.assertTrue(OfflineRecord.objects.filter(request=r).exists())

    def test_is_not_a_second_approval(self):
        r = self.rec()
        self.assertFalse(WorkflowTask.objects.filter(request=r).exists())

    def test_evidence_is_required(self):
        with self.assertRaises(app.ApplicationError):
            self.rec(reference="  ")
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_future_sanction_rejected(self):
        with self.assertRaises(app.ApplicationError):
            self.rec(sanctioned_on=date(2999, 1, 1))

    def test_overlap_is_inconsistent_and_changes_nothing(self):
        self.rec()
        with self.assertRaises(validation.LeaveValidationError):
            self.rec()
        self.assertEqual(self.bal(1, 2026, "EL"), 25)
        self.assertEqual(LeaveRequest.objects.count(), 1)

    def test_insufficient_balance_changes_nothing(self):
        with self.assertRaises(validation.LeaveValidationError):
            self.rec(end=date(2026, 12, 20))
        self.assertEqual(LeaveRequest.objects.count(), 0)


class YearEndTests(JobsBase):
    def setUp(self):
        super().setUp()
        accounts.credit_annual(1, 2026, "staff", policy.DEFAULT_PARAMS)
        accounts.credit_annual(2, 2026, "faculty", policy.DEFAULT_PARAMS)
        accounts.post(2, 2026, "VL", "debit", -11)          # 49 VL left

    def test_lapse_conversion_and_carry_forward(self):
        s = sched.process_year_end(2026)
        self.assertEqual(s["exceptions"], [])
        for uid in (1, 2):
            for t in ("CL", "RH", "SCL"):
                self.assertEqual(self.bal(uid, 2026, t), 0)
        self.assertEqual(self.bal(1, 2026, "EL"), 0)
        self.assertEqual(self.bal(1, 2027, "EL"), 30)
        self.assertEqual(self.bal(1, 2027, "COL"), 20)
        self.assertEqual(self.bal(2, 2026, "VL"), 0)
        self.assertEqual(self.bal(2, 2027, "EL"), Decimal("24.5"))      # 49 VL / 2
        self.assertFalse(LeaveAccount.objects.filter(
            user_id=2, year=2027, leave_type="VL").exists())             # VL never carries

    def test_rerun_posts_nothing_twice(self):
        sched.process_year_end(2026)
        again = sched.process_year_end(2026)
        self.assertEqual((again["lapsed"], again["converted"], again["carried"]), (0, 0, 0))
        self.assertEqual(self.bal(1, 2027, "EL"), 30)

    def test_ledger_still_matches_every_balance(self):
        sched.process_year_end(2026)
        for acct in LeaveAccount.objects.all():
            total = LeaveTransaction.objects.filter(account=acct).aggregate(s=Sum("amount"))["s"]
            self.assertEqual(total or 0, acct.balance)

    def test_next_year_credit_adds_to_carried_balances(self):
        employees = [USERS[1], UserDTO(user_id=2, username="u2", display_name="U2",
                                       kind="faculty", department="CSE")]
        sched.process_year_end(2026)
        with patch("modules.elm.services.scheduled.get_employees", return_value=employees):
            sched.credit_year(2027)
        self.assertEqual(self.bal(1, 2027, "EL"), 60)       # 30 carried + 30 credited
        self.assertEqual(self.bal(1, 2027, "COL"), 40)
        self.assertEqual(self.bal(1, 2027, "CL"), 8)
        self.assertEqual(self.bal(2, 2027, "VL"), 60)
        self.assertEqual(self.bal(2, 2027, "EL"), Decimal("24.5"))


class SlaTests(JobsBase):
    def setUp(self):
        super().setUp()
        accounts.credit_annual(1, 2026, "staff", policy.DEFAULT_PARAMS)
        self.now = timezone.now()

    def age(self, task, hours):
        WorkflowTask.objects.filter(pk=task.pk).update(created_at=self.now - timedelta(hours=hours))

    def pending_cl(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        return r, WorkflowTask.objects.get(request=r, status="open")

    def test_nothing_before_threshold(self):
        _, task = self.pending_cl()
        self.age(task, 10)
        self.assertEqual(sched.process_sla(self.now), {"reminders": 0, "escalations": 0})

    def test_reminder_goes_to_responsible_user_once(self):
        _, task = self.pending_cl()
        self.age(task, 50)
        self.assertEqual(sched.process_sla(self.now), {"reminders": 1, "escalations": 0})
        log = SlaLog.objects.get(task=task)
        self.assertEqual((log.action, log.notified_id), ("reminder", 10))
        self.assertEqual(sched.process_sla(self.now), {"reminders": 0, "escalations": 0})

    def test_escalation_goes_to_higher_authority(self):
        _, task = self.pending_cl()
        self.age(task, 100)
        self.assertEqual(sched.process_sla(self.now), {"reminders": 1, "escalations": 1})
        self.assertEqual(SlaLog.objects.get(task=task, action="escalation").notified_id, 40)

    def test_final_authority_task_escalates_to_director(self):
        r = app.submit(app.create_draft(1, "EL", MON, FRI, "rest").pk)
        app.unit_head_decide(r.pk, 10, "recommended")
        task = WorkflowTask.objects.get(request=r, stage="final", status="open")
        self.age(task, 100)
        sched.process_sla(self.now)
        self.assertEqual(SlaLog.objects.get(task=task, action="escalation").notified_id, 7)

    def test_completed_task_gets_no_action(self):
        r, task = self.pending_cl()
        app.unit_head_decide(r.pk, 10, "approved")
        self.age(task, 200)
        self.assertEqual(sched.process_sla(self.now), {"reminders": 0, "escalations": 0})
        self.assertEqual(SlaLog.objects.count(), 0)

    def test_withdrawn_request_gets_no_action(self):
        r, task = self.pending_cl()
        app.withdraw(r.pk, 1)
        self.age(task, 200)
        self.assertEqual(sched.process_sla(self.now), {"reminders": 0, "escalations": 0})
