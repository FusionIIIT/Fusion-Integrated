from datetime import date
from decimal import Decimal

from django.test import TestCase

from core.api.exceptions import BadRequestError, ConflictError
from modules.elm.models import (
    EmployeeLeaveBalance,
    LeaveApplicationTransition,
    LeaveCategory,
)
from modules.elm.services import (
    approve_leave_application,
    chargeable_days,
    process_unit_head_review,
    submit_leave_application,
    withdraw_leave_application,
)


class LeaveApplicationServiceTests(TestCase):
    def setUp(self):
        self.cl = LeaveCategory.objects.create(
            code="CL",
            label="Casual Leave",
            entitlement_days=8,
            carry_forward=False,
            continuous_counting=False,
        )
        self.el = LeaveCategory.objects.create(
            code="EL",
            label="Earned Leave",
            entitlement_days=30,
            carry_forward=True,
            continuous_counting=True,
        )

    def submit(self, code="CL", start=date(2026, 10, 26), end=date(2026, 10, 26), half_type=""):
        return submit_leave_application(
            user_id=41,
            employee_kind="staff",
            category_code=code,
            start=start,
            end=end,
            purpose="Personal leave",
            half_type=half_type,
        )

    def test_balance_is_debited_only_after_final_approval(self):
        app = self.submit(end=date(2026, 10, 27))
        balance = EmployeeLeaveBalance.objects.get(user_id=41, leave_category=self.cl)
        self.assertEqual(balance.remaining_days, Decimal("8.00"))
        self.assertEqual(balance.used_days, Decimal("0.00"))

        decided = process_unit_head_review(app.pk, "approve", 7, "Unit Head")

        balance.refresh_from_db()
        self.assertEqual(decided.status, "sanctioned")
        self.assertEqual(balance.remaining_days, Decimal("6.00"))
        self.assertEqual(balance.used_days, Decimal("2.00"))

    def test_complementary_cl_half_days_on_same_date_do_not_overlap(self):
        first = self.submit(half_type="FIRST_HALF")
        second = self.submit(half_type="SECOND_HALF")

        process_unit_head_review(first.pk, "approve", 7, "Unit Head")
        process_unit_head_review(second.pk, "approve", 7, "Unit Head")

        balance = EmployeeLeaveBalance.objects.get(user_id=41, leave_category=self.cl)
        self.assertEqual(balance.remaining_days, Decimal("7.00"))
        self.assertEqual(balance.used_days, Decimal("1.00"))

    def test_withdrawal_is_terminal_and_does_not_change_balance(self):
        app = self.submit()

        withdrawn = withdraw_leave_application(app.pk, 41)

        balance = EmployeeLeaveBalance.objects.get(user_id=41, leave_category=self.cl)
        self.assertEqual(withdrawn.status, "withdrawn")
        self.assertEqual(balance.remaining_days, Decimal("8.00"))
        self.assertEqual(balance.used_days, Decimal("0.00"))
        with self.assertRaises(ConflictError):
            process_unit_head_review(app.pk, "approve", 7, "Unit Head")

    def test_not_recommended_continues_to_a_final_decision(self):
        app = self.submit(code="EL", end=date(2026, 10, 27))
        recommendation = process_unit_head_review(app.pk, "not_recommend", 7, "Unit Head")
        decided = approve_leave_application(app.pk, "approve", 8, "Sanctioning Authority")

        balance = EmployeeLeaveBalance.objects.get(user_id=41, leave_category=self.el)
        transitions = list(
            LeaveApplicationTransition.objects.filter(application=app)
            .order_by("at", "pk")
            .values_list("to_status", flat=True)
        )
        self.assertEqual(recommendation.status, "not_recommended")
        self.assertEqual(decided.status, "sanctioned")
        self.assertEqual(balance.remaining_days, Decimal("28.00"))
        self.assertEqual(transitions, ["submitted", "not_recommended", "sanctioned"])

    def test_employee_type_and_half_day_constraints_are_enforced(self):
        with self.assertRaises(ConflictError):
            submit_leave_application(
                user_id=42,
                employee_kind="faculty",
                category_code="EL",
                start=date(2026, 10, 26),
                end=date(2026, 10, 26),
                purpose="Not eligible",
            )
        with self.assertRaises(BadRequestError):
            chargeable_days(self.cl, date(2026, 10, 26), date(2026, 10, 27), "FIRST_HALF")
