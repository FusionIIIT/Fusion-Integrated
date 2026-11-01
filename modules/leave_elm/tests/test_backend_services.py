import unittest
from unittest.mock import MagicMock, patch

from modules.leave_elm.services import leave


class TestLeaveBackendService(unittest.TestCase):
    @patch("modules.leave_elm.services.leave.LeaveBalance")
    @patch("modules.leave_elm.services.leave.LeaveApplication")
    @patch("modules.leave_elm.services.leave.SubstituteResponse")
    def test_1_application_creation_success(
        self, mock_substitute_response, mock_leave_application, mock_leave_balance
    ):
        """Test 1: Application creation service with valid inputs and successful balance deduction."""
        application_id = 42
        employee_id = "test_user_123"

        # 1. Mock Balance Check Success (10 days available)
        mock_balance_instance = mock_leave_balance.objects.get.return_value
        mock_balance_instance.available_balance = 10.0
        mock_balance_instance.save.return_value = None

        # 2. Mock Application Creation Success
        mock_app_instance = MagicMock(pk=application_id, status="pending")
        mock_leave_application.objects.create.return_value = mock_app_instance

        # 3. Mock Substitute Response Creation
        mock_substitute_response.objects.create.return_value = MagicMock()

        # Execute Service Call
        result = leave.apply_leave(
            employee_id=employee_id,
            category="EL",
            start_date_str="2024-11-01",
            end_date_str="2024-11-03",  # 3 days continuous
            reason="Vacation",
            substitute_id="S001",
            is_station_leave=False,
            is_half_day_start=False,
            is_half_day_end=False,
        )

        # Assertions
        self.assertEqual(result["application_id"], application_id)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(mock_balance_instance.available_balance, 7.0)
        mock_balance_instance.save.assert_called()

    @patch("modules.leave_elm.services.leave.LeaveBalance")
    @patch("modules.leave_elm.services.leave.LeaveApplication")
    def test_2_insufficient_balance_validation(self, mock_leave_application, mock_leave_balance):
        """Test 2: Should raise ValueError when duration exceeds available balance."""
        employee_id = "E002"

        # Mock Balance Check: Only 2 days available
        mock_balance_instance = mock_leave_balance.objects.get.return_value
        mock_balance_instance.available_balance = 2.0

        # Requesting 6 days
        with self.assertRaisesRegex(
            ValueError, "Insufficient balance.*Required: 6.0 days, Available: 2.0 days"
        ):
            leave.apply_leave(
                employee_id=employee_id,
                category="EL",
                start_date_str="2024-11-01",
                end_date_str="2024-11-06",
                reason="Vacation",
                substitute_id=None,
                is_station_leave=False,
                is_half_day_start=False,
                is_half_day_end=False,
            )

        mock_leave_application.objects.create.assert_not_called()

    @patch("modules.leave_elm.services.leave.LeaveApplication")
    def test_3_approval_state_transition(self, mock_leave_application):
        """Test 3: Test approve_application transitions status from 'pending' to 'recommended'."""
        application_id = 101
        approver_id = "A001"

        mock_app_instance = MagicMock(pk=application_id, status="pending")
        mock_leave_application.objects.get.return_value = mock_app_instance

        result = leave.approve_application(
            application_id=application_id,
            approver_id=approver_id,
            action="approve",
            notes="Looks good",
        )

        self.assertEqual(result["new_status"], "recommended")
        self.assertEqual(mock_app_instance.approved_by_id, approver_id)
        mock_app_instance.save.assert_called()

    @patch("modules.leave_elm.services.leave.LeaveApplication")
    def test_4_reject_application_transition(self, mock_leave_application):
        """Test 4: Test reject_application transitions status to 'rejected'."""
        application_id = 102
        approver_id = "A002"

        mock_app_instance = MagicMock(pk=application_id, status="pending")
        mock_leave_application.objects.get.return_value = mock_app_instance

        result = leave.reject_application(
            application_id=application_id,
            approver_id=approver_id,
            notes="Too much vacation requested.",
        )

        self.assertEqual(result["new_status"], "rejected")
        self.assertEqual(result["rejected_by"], approver_id)
        self.assertEqual(mock_app_instance.status, "rejected")
        mock_app_instance.save.assert_called()

    @patch("modules.leave_elm.services.leave.LeaveApplication")
    def test_5_repeated_action_protection(self, mock_leave_application):
        """Test 5: Test that attempting approval/rejection on a non-pending application fails."""
        application_id = 103
        approver_id = "A003"

        mock_app_instance = MagicMock(pk=application_id, status="approved")
        mock_leave_application.objects.get.return_value = mock_app_instance

        with self.assertRaisesRegex(
            ValueError, "Application is already in status: approved.*Cannot approve."
        ):
            leave.approve_application(
                application_id=application_id,
                approver_id=approver_id,
                action="approve",
                notes="Testing loop",
            )

        mock_app_instance.save.assert_not_called()
