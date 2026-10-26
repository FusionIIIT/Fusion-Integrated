from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from modules.elm.models import LeaveRequest, LeaveType, SubstituteResponse


class LeaveRequestTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.leave_type = LeaveType.objects.create(name='Sick Leave')

    def test_create_leave_request(self):
        data = {
            'leave_type': self.leave_type.id,
            'user_id': self.user.id,
            'start_date': '2023-10-01',
            'end_date': '2023-10-05',
            'reason': 'Sick'
        }
        response = self.client.post(reverse('leave-request-list'), data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LeaveRequest.objects.count(), 1)
        leave_request = LeaveRequest.objects.first()
        self.assertEqual(leave_request.user_id, self.user.id)
        self.assertEqual(leave_request.status, 'pending')

    def test_create_leave_request_for_other_user(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpassword')
        data = {
            'leave_type': self.leave_type.id,
            'user_id': other_user.id,
            'start_date': '2023-10-01',
            'end_date': '2023-10-05',
            'reason': 'Sick'
        }
        response = self.client.post(reverse('leave-request-list'), data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_update_leave_request(self):
        leave_request = LeaveRequest.objects.create(
            leave_type=self.leave_type,
            start_date='2023-10-01',
            end_date='2023-10-05',
            reason='Sick',
            user_id=self.user.id
        )
        data = {
            'leave_type': self.leave_type.id,
            'user_id': self.user.id,
            'start_date': '2023-10-02',
            'end_date': '2023-10-06',
            'reason': 'Sick'
        }
        response = self.client.put(
            reverse('leave-request-detail', args=[leave_request.id]), data
        )
        self.assertEqual(response.status_code, 200)
        leave_request.refresh_from_db()
        self.assertEqual(str(leave_request.start_date), '2023-10-02')
        self.assertEqual(str(leave_request.end_date), '2023-10-06')

    def test_update_leave_request_for_other_user(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpassword')
        leave_request = LeaveRequest.objects.create(
            leave_type=self.leave_type,
            start_date='2023-10-01',
            end_date='2023-10-05',
            reason='Sick',
            user_id=other_user.id
        )
        data = {
            'start_date': '2023-10-02',
            'end_date': '2023-10-06',
            'reason': 'Sick'
        }
        response = self.client.put(
            reverse('leave-request-detail', args=[leave_request.id]), data
        )
        self.assertEqual(response.status_code, 404)
        leave_request.refresh_from_db()
        self.assertEqual(str(leave_request.start_date), '2023-10-01')
        self.assertEqual(str(leave_request.end_date), '2023-10-05')

    def test_create_substitute_response(self):
        leave_request = LeaveRequest.objects.create(
            leave_type=self.leave_type,
            start_date='2023-10-01',
            end_date='2023-10-05',
            reason='Sick',
            user_id=self.user.id
        )
        data = {
            'leave_request': leave_request.id,
            'substitute_user_id': self.user.id,
            'response': 'accepted'
        }
        response = self.client.post(reverse('substitute-response-list'), data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SubstituteResponse.objects.count(), 1)
        substitute_response = SubstituteResponse.objects.first()
        self.assertEqual(substitute_response.leave_request_id, leave_request.id)
        self.assertEqual(substitute_response.response, 'accepted')

    def test_create_substitute_response_for_other_user(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpassword')
        leave_request = LeaveRequest.objects.create(
            leave_type=self.leave_type,
            start_date='2023-10-01',
            end_date='2023-10-05',
            reason='Sick',
            user_id=other_user.id
        )
        data = {
            'leave_request': leave_request.id,
            'response': 'accepted'
        }
        response = self.client.post(reverse('substitute-response-list'), data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SubstituteResponse.objects.count(), 0)
