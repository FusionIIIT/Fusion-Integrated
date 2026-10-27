from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from applications.elm.models import LeaveApplication, LeaveBalance

class ReviewLeaveViewTest(APITestCase):
    def setUp(self):
        # Create users
        self.applicant = User.objects.create_user(username='applicant', password='applicant123')
        self.reviewer = User.objects.create_user(username='reviewer', password='reviewer123')

        # Assign 'can_approve' permission to the reviewer
        permission, created = Permission.objects.get_or_create(
            codename='can_approve', 
            content_type=ContentType.objects.get_for_model(LeaveApplication)
        )
        self.reviewer.user_permissions.add(permission)

        # Create initial LeaveBalance record (5 days CL)
        self.leave_balance = LeaveBalance.objects.create(
            user=self.applicant, 
            year=timezone.now().year, 
            casual_leave=5
        )

        # Create AWAITING_UNIT_HEAD LeaveApplication (3 days duration)
        self.leave = LeaveApplication.objects.create(
            applicant=self.applicant,
            category='CL',
            start_date=timezone.now().date() + timezone.timedelta(days=2),
            end_date=timezone.now().date() + timezone.timedelta(days=4),
            status='AWAITING_UNIT_HEAD'
        )

    def test_approve_leave_success(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            f'/leave/application/{self.leave.pk}/review/', 
            {'decision': 'approve', 'remarks': 'Approved'}, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LeaveApplication.objects.get(pk=self.leave.pk).status, 'APPROVED')
        self.assertEqual(LeaveBalance.objects.get(user=self.applicant, year=timezone.now().year).casual_leave, 2)

    def test_approve_leave_self_approval_forbidden(self):
        self.client.force_authenticate(user=self.applicant)
        response = self.client.post(
            f'/leave/application/{self.leave.pk}/review/', 
            {'decision': 'approve', 'remarks': 'Approved'}, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_leave_insufficient_balance(self):
        self.leave_balance.casual_leave = 1
        self.leave_balance.save()
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            f'/leave/application/{self.leave.pk}/review/', 
            {'decision': 'approve', 'remarks': 'Approved'}, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient leave balance for approval.', response.data['error'])

    def test_review_nonexistent_leave(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            '/leave/application/999/review/', 
            {'decision': 'approve', 'remarks': 'Approved'}, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)