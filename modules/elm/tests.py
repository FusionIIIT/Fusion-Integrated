
from django.test import TestCase

from modules.elm.models import (
    EmployeeOfficeAssignment,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Office,
)
from modules.elm.services import (
    apply_leave,
    process_leave_approval,
    process_leave_rejection,
)


class LeaveManagementTests(TestCase):
    def setUp(self):
        self.office = Office.objects.create(
            name="Academic Office",
            code="ACADEMIC",
        )

        EmployeeOfficeAssignment.objects.create(
            user_id=101,
            office=self.office,
            is_active=True,
        )

        self.leave_type = LeaveType.objects.create(
            name="Casual Leave",
            type_code="CL",
        )

        self.balance = LeaveBalance.objects.create(
            user_id=101,
            leave_type=self.leave_type,
            current_balance=10,
        )

    def test_apply_leave_creates_pending_request(self):
        result = apply_leave(
            user_id=101,
            leave_type_id=self.leave_type.id,
            start_date_str="2026-11-02",
            end_date_str="2026-11-04",
            reason="Personal work",
        )

        self.assertEqual(result["status"], "PENDING")

        leave_request = LeaveRequest.objects.get(id=result["id"])
        self.assertEqual(leave_request.office, self.office)

    def test_apply_leave_rejects_invalid_date_range(self):
        result = apply_leave(
            user_id=101,
            leave_type_id=self.leave_type.id,
            start_date_str="2026-11-05",
            end_date_str="2026-11-02",
            reason="Invalid dates",
        )

        self.assertIn("error", result)

    def test_apply_leave_rejects_insufficient_balance(self):
        result = apply_leave(
            user_id=101,
            leave_type_id=self.leave_type.id,
            start_date_str="2026-11-01",
            end_date_str="2026-11-19",
            reason="Long leave",
        )

        self.assertIn("error", result)

    def test_approval_deducts_balance(self):
        result = apply_leave(
            user_id=101,
            leave_type_id=self.leave_type.id,
            start_date_str="2026-11-02",
            end_date_str="2026-11-04",
            reason="Personal work",
        )

        approval = process_leave_approval(
            request_id=result["id"],
            approver_id=202,
        )

        self.assertEqual(approval["status"], "success")

        self.balance.refresh_from_db()
        self.assertEqual(self.balance.current_balance, 7)

    def test_rejection_does_not_deduct_balance(self):
        result = apply_leave(
            user_id=101,
            leave_type_id=self.leave_type.id,
            start_date_str="2026-11-02",
            end_date_str="2026-11-04",
            reason="Personal work",
        )

        rejection = process_leave_rejection(
            request_id=result["id"],
            approver_id=202,
            reason="Insufficient staffing",
        )

        self.assertEqual(rejection["status"], "success")

        self.balance.refresh_from_db()
        self.assertEqual(self.balance.current_balance, 10)

    def test_approved_request_cannot_be_approved_twice(self):
        result = apply_leave(
            user_id=101,
            leave_type_id=self.leave_type.id,
            start_date_str="2026-11-02",
            end_date_str="2026-11-04",
            reason="Personal work",
        )

        first_approval = process_leave_approval(
            request_id=result["id"],
            approver_id=202,
        )

        second_approval = process_leave_approval(
            request_id=result["id"],
            approver_id=203,
        )

        self.assertEqual(first_approval["status"], "success")
        self.assertIn("error", second_approval)

        self.balance.refresh_from_db()
        self.assertEqual(self.balance.current_balance, 7)

    def test_apply_leave_requires_active_office_assignment(self):
        result = apply_leave(
            user_id=999,
            leave_type_id=self.leave_type.id,
            start_date_str="2026-11-02",
            end_date_str="2026-11-04",
            reason="Personal work",
        )

        self.assertIn("error", result)
        self.assertIn("office assignment", result["error"].lower())

        self.assertFalse(
            LeaveRequest.objects.filter(user_id=999).exists()
        )
