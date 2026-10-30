"""Integration tests for leave services and workflow."""
from datetime import date
from decimal import Decimal
from django.test import TestCase

from core.api.exceptions import ConflictError
from modules.leave.domain.constants import (
    DECISION_APPROVE,
    DECISION_NOT_RECOMMEND,
    DECISION_RECOMMEND,
    DECISION_REJECT,
    HALF_DAY_FIRST,
    HALF_DAY_SECOND,
    LEAVE_CL,
    LEAVE_COL,
    LEAVE_EL,
    LEAVE_SCL,
    LEAVE_VL,
    STATUS_APPROVED,
    STATUS_AWAITING_DIRECTOR_SELF_SANCTION,
    STATUS_AWAITING_FINAL_SANCTION,
    STATUS_AWAITING_SUBSTITUTE,
    STATUS_AWAITING_UNIT_HEAD,
    STATUS_CANCELLED,
    STATUS_CLOSED,
    STATUS_REJECTED,
    STATUS_WITHDRAWN,
    SUBSTITUTE_ACCEPTED,
    SUBSTITUTE_DECLINED,
)
from modules.leave.models import LeaveBalance, LeaveRequest
from modules.leave.services.leave import (
    apply_leave,
    decide_cancellation,
    ensure_user_balances,
    modify_pending_request,
    process_year_end,
    request_cancellation,
    respond_substitute,
    review_unit_head,
    sanction_final,
    submit_extension,
    submit_resumption,
    verify_resumption,
    withdraw_pending_request,
)


class TestLeaveServices(TestCase):
    def setUp(self):
        super().setUp()
        self.emp_id = 101
        self.sub_id = 102
        self.reviewer_id = 201
        self.director_id = 999

        # Seed balances for employee and substitute
        ensure_user_balances(self.emp_id, kind="staff", year=2026)
        ensure_user_balances(self.sub_id, kind="staff", year=2026)

    def test_apply_cl_half_day_and_unit_head_approval(self):
        """WF-EL-01: Apply for half-day CL, Unit Head acts as final sanctioning authority (BR-EL-016)."""
        d = date(2026, 11, 2)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_CL,
            start_date=d,
            end_date=d,
            half_day=HALF_DAY_FIRST,
            purpose="Doctor appointment",
        )
        self.assertEqual(req.status, STATUS_AWAITING_UNIT_HEAD)
        self.assertEqual(req.requested_days, Decimal("0.5"))

        # Unit head approves CL
        approved_req = review_unit_head(
            request_id=req.pk,
            reviewer_user_id=self.reviewer_id,
            decision=DECISION_APPROVE,
            remarks="Approved",
        )
        self.assertEqual(approved_req.status, STATUS_APPROVED)

        # Balance deducted by 0.5
        bal = LeaveBalance.objects.get(user_id=self.emp_id, year=2026, category=LEAVE_CL)
        self.assertEqual(bal.balance, Decimal("7.5"))
        self.assertEqual(bal.availed, Decimal("0.5"))

    def test_substitute_workflow_gate(self):
        """BR-EL-014, BR-EL-015: Substitute must consent before Unit Head review."""
        start = date(2026, 11, 9)
        end = date(2026, 11, 10)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_CL,
            start_date=start,
            end_date=end,
            purpose="Personal work",
            substitute_user_id=self.sub_id,
        )
        self.assertEqual(req.status, STATUS_AWAITING_SUBSTITUTE)

        # Substitute accepts
        req = respond_substitute(req.pk, self.sub_id, accept=True, remarks="I will cover classes.")
        self.assertEqual(req.substitute_status, SUBSTITUTE_ACCEPTED)
        self.assertEqual(req.status, STATUS_AWAITING_UNIT_HEAD)

    def test_substitute_decline_keeps_approval_blocked(self):
        """BR-EL-015: Substitute decline keeps approval routing blocked."""
        start = date(2026, 11, 12)
        end = date(2026, 11, 13)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_CL,
            start_date=start,
            end_date=end,
            purpose="Personal work",
            substitute_user_id=self.sub_id,
        )
        req = respond_substitute(req.pk, self.sub_id, accept=False, remarks="Traveling.")
        self.assertEqual(req.substitute_status, SUBSTITUTE_DECLINED)
        self.assertEqual(req.status, STATUS_AWAITING_SUBSTITUTE)

    def test_higher_sanction_flow_el(self):
        """WF-EL-01, BR-EL-017, BR-EL-018: Unit Head recommends EL -> Final Authority sanctions."""
        start = date(2026, 11, 16)
        end = date(2026, 11, 18)  # 3 days
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_EL,
            start_date=start,
            end_date=end,
            purpose="Family function",
        )
        self.assertEqual(req.status, STATUS_AWAITING_UNIT_HEAD)

        # Unit head records recommendation
        req = review_unit_head(req.pk, self.reviewer_id, decision=DECISION_RECOMMEND)
        self.assertEqual(req.status, STATUS_AWAITING_FINAL_SANCTION)

        # Sanctioning authority approves
        req = sanction_final(req.pk, self.director_id, decision=DECISION_APPROVE)
        self.assertEqual(req.status, STATUS_APPROVED)

        el_bal = LeaveBalance.objects.get(user_id=self.emp_id, year=2026, category=LEAVE_EL)
        self.assertEqual(el_bal.balance, Decimal("27.0"))

    def test_unit_head_cannot_reject_el_or_scl_directly(self):
        """BR-EL-017: Unit Head does not make final rejection decision for SCL/EL/COL/VL."""
        start = date(2026, 11, 16)
        end = date(2026, 11, 18)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_EL,
            start_date=start,
            end_date=end,
            purpose="Vacation",
        )
        with self.assertRaises(ConflictError):
            review_unit_head(req.pk, self.reviewer_id, decision=DECISION_REJECT)

    def test_station_leave_validation(self):
        """BR-EL-013: Station Leave date coverage and contact details validation."""
        start = date(2026, 11, 16)
        end = date(2026, 11, 18)

        # Missing dates
        with self.assertRaises(ConflictError):
            apply_leave(
                user_id=self.emp_id,
                category=LEAVE_CL,
                start_date=start,
                end_date=end,
                purpose="Trip",
                station_leave=True,
            )

        # Station dates do not cover leave range
        with self.assertRaises(ConflictError):
            apply_leave(
                user_id=self.emp_id,
                category=LEAVE_CL,
                start_date=start,
                end_date=end,
                purpose="Trip",
                station_leave=True,
                station_start_date=date(2026, 11, 17),  # starts after leave start
                station_end_date=end,
                station_address="Hotel Delhi",
                station_contact="9876543210",
            )

        # Valid station leave
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_CL,
            start_date=start,
            end_date=end,
            purpose="Trip",
            station_leave=True,
            station_start_date=date(2026, 11, 15),
            station_end_date=date(2026, 11, 19),
            station_address="Hotel Delhi",
            station_contact="9876543210",
        )
        self.assertTrue(req.station_leave)
        self.assertEqual(req.station_address, "Hotel Delhi")

    def test_extension_boundary_validation(self):
        """BR-EL-025: Extension start date must be after parent leave end date."""
        start = date(2026, 11, 16)
        end = date(2026, 11, 18)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_EL,
            start_date=start,
            end_date=end,
            purpose="Conference",
        )
        review_unit_head(req.pk, self.reviewer_id, decision=DECISION_RECOMMEND)
        sanction_final(req.pk, self.director_id, decision=DECISION_APPROVE)

        # Extension starting on or before end_date fails
        with self.assertRaises(ConflictError):
            submit_extension(
                parent_leave_id=req.pk,
                user_id=self.emp_id,
                extension_start=end,
                extension_end=date(2026, 11, 20),
                purpose="Extended stay",
            )

        # Extension starting after end_date succeeds
        ext = submit_extension(
            parent_leave_id=req.pk,
            user_id=self.emp_id,
            extension_start=date(2026, 11, 19),
            extension_end=date(2026, 11, 20),
            purpose="Extended stay",
        )
        self.assertEqual(ext.parent_leave_id, req.pk)

    def test_director_self_sanction_flow(self):
        """BR-EL-020: Director as applicant uses Director self-sanction flow."""
        ensure_user_balances(self.director_id, kind="faculty", year=2026)
        start = date(2026, 11, 23)
        end = date(2026, 11, 24)
        req = apply_leave(
            user_id=self.director_id,
            category=LEAVE_CL,
            start_date=start,
            end_date=end,
            purpose="Institute official business",
            is_director=True,
        )
        self.assertEqual(req.status, STATUS_AWAITING_DIRECTOR_SELF_SANCTION)

        # Director self-sanctions
        req = sanction_final(req.pk, self.director_id, decision=DECISION_APPROVE)
        self.assertEqual(req.status, STATUS_APPROVED)

    def test_modify_and_withdraw_pending_request(self):
        """WF-EL-02, BR-EL-021, BR-EL-022: Modifying and immediately withdrawing pending requests."""
        start = date(2026, 11, 26)
        end = date(2026, 11, 26)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_CL,
            start_date=start,
            end_date=end,
            purpose="Bank visit",
        )

        # Modify to next day
        new_date = date(2026, 11, 27)
        req = modify_pending_request(
            request_id=req.pk,
            user_id=self.emp_id,
            start_date=new_date,
            end_date=new_date,
            purpose="Bank visit rescheduled",
        )
        self.assertEqual(req.start_date, new_date)

        # Withdraw
        req = withdraw_pending_request(req.pk, self.emp_id)
        self.assertEqual(req.status, STATUS_WITHDRAWN)

    def test_cancellation_and_balance_restoration(self):
        """WF-EL-03, BR-EL-023: Cancellation before leave starts restores balance."""
        start = date(2026, 12, 1)
        end = date(2026, 12, 2)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_CL,
            start_date=start,
            end_date=end,
            purpose="Wedding",
        )
        review_unit_head(req.pk, self.reviewer_id, decision=DECISION_APPROVE)
        bal_before = LeaveBalance.objects.get(user_id=self.emp_id, year=2026, category=LEAVE_CL).balance

        # Request cancellation
        req = request_cancellation(req.pk, self.emp_id)

        # Approve cancellation
        req = decide_cancellation(req.pk, self.reviewer_id, approve=True)
        self.assertEqual(req.status, STATUS_CANCELLED)

        # Balance restored
        bal_after = LeaveBalance.objects.get(user_id=self.emp_id, year=2026, category=LEAVE_CL).balance
        self.assertEqual(bal_after, bal_before + Decimal("2.0"))

    def test_duty_resumption_and_early_return_restoration(self):
        """WF-EL-05, BR-EL-027, BR-EL-028: Early resumption restores unused leave days."""
        # Employee takes 5 days EL (Mon to Fri)
        start = date(2026, 12, 7)
        end = date(2026, 12, 11)
        req = apply_leave(
            user_id=self.emp_id,
            category=LEAVE_EL,
            start_date=start,
            end_date=end,
            purpose="Tour",
        )
        review_unit_head(req.pk, self.reviewer_id, decision=DECISION_RECOMMEND)
        sanction_final(req.pk, self.director_id, decision=DECISION_APPROVE)

        bal_after_approval = LeaveBalance.objects.get(user_id=self.emp_id, year=2026, category=LEAVE_EL).balance

        # Employee returns early on Thursday (returned on 10th Dec, unused 10th and 11th = 2 days)
        submit_resumption(req.pk, self.emp_id, actual_date=date(2026, 12, 10))
        req = verify_resumption(req.pk, verifier_user_id=self.reviewer_id)

        self.assertEqual(req.status, STATUS_CLOSED)
        self.assertEqual(req.restored_days, Decimal("2.0"))

        bal_after_closure = LeaveBalance.objects.get(user_id=self.emp_id, year=2026, category=LEAVE_EL).balance
        self.assertEqual(bal_after_closure, bal_after_approval + Decimal("2.0"))

    def test_year_end_processing(self):
        """WF-EL-07, BR-EL-002, BR-EL-007: Year-end lapse of CL, 2:1 VL to EL conversion, and EL/COL carry-forward."""
        faculty_id = 501
        ensure_user_balances(faculty_id, kind="faculty", year=2026)

        # Faculty has 60 VL and 8 CL
        process_year_end(year=2026)

        # CL lapses to 0
        cl_bal = LeaveBalance.objects.get(user_id=faculty_id, year=2026, category=LEAVE_CL)
        self.assertEqual(cl_bal.balance, Decimal("0.0"))
        self.assertEqual(cl_bal.lapsed, Decimal("8.0"))

        # VL lapses and converts 2:1 (60 VL -> 30 EL)
        vl_bal = LeaveBalance.objects.get(user_id=faculty_id, year=2026, category=LEAVE_VL)
        self.assertEqual(vl_bal.balance, Decimal("0.0"))
        self.assertEqual(vl_bal.lapsed, Decimal("60.0"))

        el_bal = LeaveBalance.objects.get(user_id=faculty_id, year=2026, category=LEAVE_EL)
        self.assertEqual(el_bal.balance, Decimal("30.0"))

        # EL carried forward into 2027
        el_2027 = LeaveBalance.objects.get(user_id=faculty_id, year=2027, category=LEAVE_EL)
        self.assertEqual(el_2027.balance, Decimal("30.0"))
