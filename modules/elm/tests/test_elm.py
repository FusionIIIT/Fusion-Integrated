from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from modules.elm.models.leave import EmployeeLeave, LeaveBalance, LeaveType, LeaveStatus

User = get_user_model()

class EmployeeLeaveManagementTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='24bcs205',
            email='rahul@iiitdmj.ac.in',
            password='testpassword'
        )
        self.unit_head = User.objects.create_user(
            username='unithead',
            email='unithead@iiitdmj.ac.in',
            password='testpassword'
        )
        self.balance = LeaveBalance.objects.create(
            user=self.user,
            year=2026,
            leave_type=LeaveType.CASUAL,
            credited=Decimal('10.0'),
            consumed=Decimal('0.0'),
            available=Decimal('10.0')
        )
        self.client.force_authenticate(user=self.user)

    def test_leave_application_date_validation(self):
        """Test model validation prevents start_date > end_date."""
        leave = EmployeeLeave(
            applicant=self.user,
            leave_type=LeaveType.CASUAL,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 5),
            purpose='Invalid dates'
        )
        with self.assertRaises(ValidationError):
            leave.clean()

    def test_half_day_duration_calculation(self):
        """Test is_half_day sets duration_days to 0.5."""
        leave = EmployeeLeave.objects.create(
            applicant=self.user,
            leave_type=LeaveType.CASUAL,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 1),
            is_half_day=True,
            half_day_slot='FIRST',
            purpose='Doctor appointment'
        )
        self.assertEqual(leave.duration_days, Decimal('0.5'))

    def test_leave_approval_deducts_balance(self):
        """Test unit_head approval atomically updates LeaveBalance."""
        leave = EmployeeLeave.objects.create(
            applicant=self.user,
            leave_type=LeaveType.CASUAL,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 3),
            duration_days=Decimal('3.0'),
            purpose='Family function',
            status=LeaveStatus.SUBMITTED
        )

        self.client.force_authenticate(user=self.unit_head)
        url = f'/api/v1/elm/leaves/{leave.id}/unit_head_decision/'
        response = self.client.post(url, {'decision': 'APPROVE', 'remarks': 'Approved by HOD'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.available, Decimal('7.0'))
        self.assertEqual(self.balance.consumed, Decimal('3.0'))

        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveStatus.APPROVED)
        self.assertEqual(leave.unit_head_remarks, 'Approved by HOD')

    def test_insufficient_balance_rejection(self):
        """Test approving when requested duration exceeds available balance returns 400."""
        self.balance.available = Decimal('1.0')
        self.balance.save()

        leave = EmployeeLeave.objects.create(
            applicant=self.user,
            leave_type=LeaveType.CASUAL,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            duration_days=Decimal('5.0'),
            purpose='Long trip',
            status=LeaveStatus.SUBMITTED
        )

        self.client.force_authenticate(user=self.unit_head)
        url = f'/api/v1/elm/leaves/{leave.id}/unit_head_decision/'
        response = self.client.post(url, {'decision': 'APPROVE'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient leave balance', response.data['error'])

    def test_unit_head_reviews_endpoint(self):
        """Test endpoint returns all SUBMITTED leaves awaiting review."""
        EmployeeLeave.objects.create(
            applicant=self.user,
            leave_type=LeaveType.CASUAL,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 2),
            duration_days=Decimal('2.0'),
            purpose='Submitted leave',
            status=LeaveStatus.SUBMITTED
        )
        EmployeeLeave.objects.create(
            applicant=self.user,
            leave_type=LeaveType.CASUAL,
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 4),
            duration_days=Decimal('2.0'),
            purpose='Draft leave',
            status=LeaveStatus.DRAFT
        )

        self.client.force_authenticate(user=self.unit_head)
        url = '/api/v1/elm/leaves/unit_head_reviews/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        for item in response.data:
            self.assertEqual(item['status'], LeaveStatus.SUBMITTED)
