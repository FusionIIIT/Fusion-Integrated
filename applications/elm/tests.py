from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from applications.elm.models import LeaveApplication, LeaveBalance, LeaveBalanceHistory

User = get_user_model()


class ReviewLeaveViewTests(TestCase):

    def setUp(self):
        # Create applicant and reviewer users
        self.applicant = User.objects.create_user(username='applicant', password='password123')
        self.reviewer = User.objects.create_user(username='reviewer', password='password123')

        # Create LeaveApplication owned by applicant
        self.leave_application = LeaveApplication.objects.create(
            applicant=self.applicant,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=4),  # 5-day duration
            category='CL',
            status='PENDING'
        )

        # Create LeaveBalance for the applicant in the current year
        self.leave_balance = LeaveBalance.objects.create(
            user=self.applicant,
            year=timezone.now().year,
            casual_leave=10
        )

    def test_approve_leave_success(self):
        # Authenticate as reviewer (non-applicant)
        self.client.force_login(self.reviewer)

        payload = {'decision': 'approve', 'remarks': 'Approved by unit head'}
        response = self.client.post(
            reverse('review_leave', args=[self.leave_application.id]),
            data=payload,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check LeaveApplication status update
        self.leave_application.refresh_from_db()
        self.assertEqual(self.leave_application.status, 'APPROVED')

        # Check LeaveBalance deduction (10 - 5 = 5)
        self.leave_balance.refresh_from_db()
        self.assertEqual(self.leave_balance.casual_leave, 5)

        # Check LeaveBalanceHistory creation
        self.assertTrue(
            LeaveBalanceHistory.objects.filter(
                applicant=self.applicant,
                leave_application=self.leave_application,
                category='CL',
                previous_balance=10,
                new_balance=5,
                action_by=self.reviewer,
                action='DEDUCT'
            ).exists()
        )

    def test_approve_leave_self_approval_forbidden(self):
        # Authenticate as applicant trying to self-approve
        self.client.force_login(self.applicant)

        payload = {'decision': 'approve'}
        response = self.client.post(
            reverse('review_leave', args=[self.leave_application.id]),
            data=payload,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.leave_application.refresh_from_db()
        self.assertEqual(self.leave_application.status, 'PENDING')

    def test_approve_leave_insufficient_balance(self):
        # Set balance lower than requested duration (duration = 5 days)
        self.leave_balance.casual_leave = 3
        self.leave_balance.save()

        self.client.force_login(self.reviewer)

        payload = {'decision': 'approve'}
        response = self.client.post(
            reverse('review_leave', args=[self.leave_application.id]),
            data=payload,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'Insufficient leave balance for approval.')

    def test_review_nonexistent_leave(self):
        self.client.force_login(self.reviewer)

        payload = {'decision': 'approve'}
        response = self.client.post(
            reverse('review_leave', args=[99999]),
            data=payload,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)