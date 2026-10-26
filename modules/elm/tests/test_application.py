from datetime import date
from unittest.mock import patch

from django.test import TestCase

from modules.directory.contracts import UserDTO
from modules.elm.models import (
    CalendarDay,
    HierarchyRule,
    HolidayCalendar,
    LeaveAccount,
    LeavePolicy,
    WorkflowTask,
)
from modules.elm.services import accounts, policy, validation, workflow
from modules.elm.services import applications as app

MON = date(2026, 11, 2)
FRI = date(2026, 11, 6)
USERS = {i: UserDTO(user_id=i, username=f"u{i}", display_name=f"U{i}",
                    kind="staff", department="CSE") for i in (1, 2, 3, 7, 10, 20, 40)}
USERS[50] = UserDTO(user_id=50, username="u50", display_name="Student 50",
                    kind="student", department="CSE")
USERS[60] = UserDTO(user_id=60, username="u60", display_name="Faculty 60",
                    kind="faculty", department="CSE")


class AppTests(TestCase):
    def setUp(self):
        p = patch("modules.elm.services.applications.get_users",
                  side_effect=lambda ids: {i: USERS[i] for i in ids if i in USERS})
        p.start()
        self.addCleanup(p.stop)
        policy.publish_policy(LeavePolicy.objects.create(version=1, params=policy.DEFAULT_PARAMS))
        policy.publish_calendar(HolidayCalendar.objects.create(year=2026, version=1))
        for uid in (1, 2, 3, 7):
            accounts.credit_annual(uid, 2026, "staff", policy.DEFAULT_PARAMS)
        accounts.credit_annual(60, 2026, "faculty", policy.DEFAULT_PARAMS)
        self.rule("unit_head", 10)
        self.rule("final", 40)

    def rule(self, stage, approver, **kw):
        return HierarchyRule.objects.create(
            stage=stage, approver_id=approver, status="published", **kw)

    def bal(self, uid, leave_type):
        return LeaveAccount.objects.get(user_id=uid, year=2026, leave_type=leave_type).balance

    def test_cl_is_decided_by_unit_head(self):
        r = app.create_draft(1, "CL", MON, MON, "personal")
        r = app.submit(r.pk)
        self.assertEqual(r.status, "awaiting_unit_head")
        r = app.unit_head_decide(r.pk, 10, "approved")
        self.assertEqual(r.status, "approved")
        self.assertEqual(self.bal(1, "CL"), 7)

    def test_el_goes_to_final_without_establishment(self):
        r = app.submit(app.create_draft(1, "EL", MON, FRI, "rest").pk)
        r = app.unit_head_decide(r.pk, 10, "not_recommended")
        self.assertEqual(r.status, "awaiting_final")
        r = app.final_decide(r.pk, 40, "approved")
        self.assertEqual(r.status, "approved")
        self.assertEqual(self.bal(1, "EL"), 25)

    def test_el_with_establishment_step(self):
        self.rule("establishment", 20, leave_type="EL")
        r = app.submit(app.create_draft(1, "EL", MON, FRI, "rest").pk)
        r = app.unit_head_decide(r.pk, 10, "recommended")
        self.assertEqual(r.status, "awaiting_establishment")
        r = app.establishment_route(r.pk, 20)
        self.assertEqual(r.status, "awaiting_final")

    def test_only_task_holder_can_decide(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        with self.assertRaises(app.ApplicationError):
            app.unit_head_decide(r.pk, 99, "approved")

    def test_unit_head_cannot_reject_el(self):
        r = app.submit(app.create_draft(1, "EL", MON, FRI, "rest").pk)
        with self.assertRaises(workflow.TransitionError):
            app.unit_head_decide(r.pk, 10, "rejected")

    def test_substitute_gate_blocks_routing_until_accept(self):
        d = app.create_draft(1, "EL", MON, FRI, "rest", substitute_required=True)
        r = app.submit(d.pk, nominee_id=2)
        self.assertEqual(r.status, "awaiting_substitute")
        self.assertFalse(WorkflowTask.objects.filter(request=r, stage="unit_head").exists())
        r = app.respond_substitute(r.pk, 2, accept=True)
        self.assertEqual(r.status, "awaiting_unit_head")

    def test_decline_keeps_gate_closed_then_renominate(self):
        d = app.create_draft(1, "EL", MON, FRI, "rest", substitute_required=True)
        r = app.submit(d.pk, nominee_id=2)
        r = app.respond_substitute(r.pk, 2, accept=False)
        self.assertEqual(r.status, "awaiting_substitute")
        app.nominate_substitute(r.pk, 1, 3)
        r = app.respond_substitute(r.pk, 3, accept=True)
        self.assertEqual(r.status, "awaiting_unit_head")

    def test_substitute_must_be_free(self):
        other = app.create_draft(2, "EL", MON, FRI, "away")
        app.submit(other.pk)
        d = app.create_draft(1, "EL", MON, FRI, "rest", substitute_required=True)
        with self.assertRaises(validation.LeaveValidationError):
            app.submit(d.pk, nominee_id=2)

    def test_withdraw_closes_tasks_and_blocks_decisions(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        r = app.withdraw(r.pk, 1)
        self.assertEqual(r.status, "withdrawn")
        self.assertFalse(WorkflowTask.objects.filter(request=r, status="open").exists())
        with self.assertRaises(app.ApplicationError):
            app.unit_head_decide(r.pk, 10, "approved")

    def test_cannot_withdraw_after_approval(self):
        r = app.submit(app.create_draft(1, "CL", MON, MON, "x").pk)
        app.unit_head_decide(r.pk, 10, "approved")
        with self.assertRaises(workflow.TransitionError):
            app.withdraw(r.pk, 1)

    def test_insufficient_balance_rejected_at_draft(self):
        with self.assertRaises(validation.LeaveValidationError):
            app.create_draft(1, "CL", MON, date(2026, 11, 13), "too long")   # 10 weekdays > 8

    def test_director_self_sanction(self):
        self.rule("director", 7)
        r = app.submit(app.create_draft(7, "EL", MON, FRI, "rest").pk)
        self.assertEqual(r.status, "awaiting_director_self")
        r = app.final_decide(r.pk, 7, "approved")
        self.assertEqual(r.status, "approved")

    def test_student_user_cannot_apply_for_leave(self):
        with self.assertRaises(app.ApplicationError) as cm:
            app.create_draft(50, "CL", MON, MON, "studying")
        self.assertIn("Only employees", str(cm.exception))

    def test_non_employee_substitute_rejected(self):
        d = app.create_draft(1, "EL", MON, FRI, "rest", substitute_required=True)
        with self.assertRaises(app.ApplicationError) as cm:
            app.submit(d.pk, nominee_id=50)
        self.assertIn("Only employees", str(cm.exception))

    def test_staff_cannot_request_vacation_leave(self):
        with self.assertRaises(validation.LeaveValidationError) as cm:
            app.create_draft(1, "VL", MON, FRI, "vacation")
        self.assertIn("Vacation Leave (VL) is for faculty only", str(cm.exception))

    def test_faculty_can_request_vacation_leave(self):
        cal = HolidayCalendar.objects.get(year=2026)
        for offset in range(5):
            CalendarDay.objects.create(
                calendar=cal,
                date=MON + __import__("datetime").timedelta(days=offset),
                kind="vacation",
            )
        d = app.create_draft(60, "VL", MON, FRI, "summer research")
        self.assertEqual(d.leave_type, "VL")
        self.assertEqual(d.days, 5)

    def test_cross_year_cl_rejected(self):
        with self.assertRaises(validation.LeaveValidationError) as cm:
            app.create_draft(1, "CL", date(2026, 12, 31), date(2027, 1, 2), "new year")
        self.assertIn("cannot span calendar years", str(cm.exception))

    def test_station_leave_outside_jabalpur_requires_station_address(self):
        with self.assertRaises(validation.LeaveValidationError) as cm:
            app.create_draft(1, "CL", MON, MON, "conf", outside_station=True, station_address=" ")
        self.assertIn("station_address is required", str(cm.exception))

