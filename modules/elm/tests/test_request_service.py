from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from modules.elm.models import (
    LeaveAccount, LeaveBalanceTransaction, LeaveCalendarDay, LeaveRequest,
    LeaveRequestTransition, LeaveTypePolicy,
)
from modules.elm.services.requests import (
    calculate_requested_days, decide_leave_request, submit_leave_request,
    withdraw_leave_request,
)


class SubmitLeaveRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.casual_leave = LeaveTypePolicy.objects.create(
            code=LeaveTypePolicy.CL,
            annual_allowance=Decimal("8.00"),
            carry_forward=False,
            continuous_calendar_days=False,
            employee_category="any",
        )
        cls.actor = SimpleNamespace(user_id=101)
        cls.account = LeaveAccount.objects.create(
            user_id=101, employee_category="any", leave_type=cls.casual_leave,
            leave_year=2026, balance_days=Decimal("8.00"),
        )

    def submit(self, **overrides):
        values = {
            "actor": self.actor,
            "leave_type_id": self.casual_leave.pk,
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 2),
            "start_session": "full",
            "end_session": "full",
            "requested_days": Decimal("1.00"),
            "reason": "Personal work",
            "employee_category": "any",
        }
        values.update(overrides)
        return submit_leave_request(**values)

    def test_submission_creates_request_and_audit_transition(self):
        request = self.submit()
        self.assertEqual(request.user_id, self.actor.user_id)
        self.assertEqual(request.status, LeaveRequest.PENDING_UNIT_HEAD)
        transition = LeaveRequestTransition.objects.get(request=request)
        self.assertEqual(transition.action, "submitted")
        self.assertEqual(transition.to_status, LeaveRequest.PENDING_UNIT_HEAD)

    def test_end_date_before_start_date_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.submit(end_date=date(2026, 11, 1))
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_zero_days_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.submit(requested_days=Decimal("0.00"))
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_blank_reason_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.submit(reason="  ")
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_inactive_leave_type_is_rejected(self):
        self.casual_leave.is_active = False
        self.casual_leave.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            self.submit()
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_employee_category_mismatch_is_rejected(self):
        self.casual_leave.employee_category = "faculty"
        self.casual_leave.save(update_fields=["employee_category"])
        with self.assertRaises(ValidationError):
            self.submit(employee_category="non_faculty")
        self.assertEqual(LeaveRequest.objects.count(), 0)


    def test_client_total_is_not_trusted_and_balance_is_reserved(self):
        row = self.submit(requested_days=Decimal("99.00"))
        self.assertEqual(row.requested_days, Decimal("1.00"))
        with self.assertRaises(ValidationError):
            self.submit(start_date=date(2026, 11, 3), end_date=date(2026, 11, 12),
                        requested_days=Decimal("1.00"))


    def test_approved_leave_is_not_reserved_twice(self):
        first = self.submit()
        decide_leave_request(actor=SimpleNamespace(user_id=202), request_id=first.pk,
                             decision="approve", reason="Approved")
        # The approved day has already reduced the account from 8 to 7.
        # A further 7-day request should not have the approved day subtracted again.
        row = self.submit(start_date=date(2026, 11, 3), end_date=date(2026, 11, 11))
        self.assertEqual(row.requested_days, Decimal("7.00"))

    def test_cross_year_request_is_rejected_until_allocation_is_configured(self):
        with self.assertRaises(ValidationError):
            self.submit(start_date=date(2026, 12, 30), end_date=date(2027, 1, 4))
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_working_day_calculation_excludes_weekends(self):
        days = calculate_requested_days(
            policy=self.casual_leave, start_date=date(2026, 11, 6),
            end_date=date(2026, 11, 9), start_session="full", end_session="full",
        )
        self.assertEqual(days, Decimal("2.00"))

    def test_published_closed_holiday_is_excluded_from_casual_leave(self):
        LeaveCalendarDay.objects.create(
            date=date(2026, 11, 9), day_type=LeaveCalendarDay.CLOSED_HOLIDAY,
            title="Institute Holiday", published=True,
        )
        days = calculate_requested_days(
            policy=self.casual_leave, start_date=date(2026, 11, 9),
            end_date=date(2026, 11, 10), start_session="full", end_session="full",
        )
        self.assertEqual(days, Decimal("1.00"))

    def test_withdraw_pending_request_is_audited(self):
        row = self.submit()
        withdrawn = withdraw_leave_request(actor=self.actor, request_id=row.pk, reason="Plans changed")
        self.assertEqual(withdrawn.status, LeaveRequest.WITHDRAWN)
        self.assertEqual(withdrawn.transitions.order_by("-pk").first().action, "withdrawn")

    def test_cl_approval_debits_balance_once(self):
        row = self.submit()
        decided = decide_leave_request(actor=SimpleNamespace(user_id=202), request_id=row.pk,
                                       decision="approve", reason="Approved")
        self.assertEqual(decided.status, LeaveRequest.APPROVED)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_days, Decimal("7.00"))
        self.assertEqual(LeaveBalanceTransaction.objects.filter(request=row).count(), 1)

    def test_cl_cannot_be_recommended_instead_of_finalized(self):
        row = self.submit()
        with self.assertRaises(ValidationError):
            decide_leave_request(actor=SimpleNamespace(user_id=202), request_id=row.pk,
                                 decision="recommend")
        row.refresh_from_db()
        self.assertEqual(row.status, LeaveRequest.PENDING_UNIT_HEAD)


    def test_distinct_half_day_requests_can_share_one_date(self):
        first_half = self.submit(start_session="first_half", end_session="first_half",
                                 requested_days=Decimal("1.00"))
        second_half = self.submit(start_session="second_half", end_session="second_half",
                                  requested_days=Decimal("1.00"))
        self.assertEqual(first_half.requested_days, Decimal("0.50"))
        self.assertEqual(second_half.requested_days, Decimal("0.50"))

    def test_same_half_day_overlap_is_rejected(self):
        self.submit(start_session="first_half", end_session="first_half")
        with self.assertRaises(ValidationError):
            self.submit(start_session="first_half", end_session="first_half")

    def test_restricted_holiday_requires_published_calendar_day(self):
        rh = LeaveTypePolicy.objects.create(
            code=LeaveTypePolicy.RH, annual_allowance=Decimal("2.00"),
            carry_forward=False, continuous_calendar_days=False, employee_category="any",
        )
        LeaveAccount.objects.create(user_id=101, employee_category="any", leave_type=rh,
                                    leave_year=2026, balance_days=Decimal("2.00"))
        with self.assertRaises(ValidationError):
            self.submit(leave_type_id=rh.pk)
        LeaveCalendarDay.objects.create(date=date(2026, 11, 2), day_type=LeaveCalendarDay.RH_DAY,
                                        title="Published RH", published=True)
        row = self.submit(leave_type_id=rh.pk)
        self.assertEqual(row.leave_type.code, LeaveTypePolicy.RH)
