from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from applications.leave.models import LeaveType, LeaveBalance, LeaveRequest, LeaveWorkflowHistory
from applications.leave.views import LeaveRequestViewSet

User = get_user_model()

class LeaveWorkflowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.emp = User.objects.create_user(username='emp_user', password='password123')
        self.reviewer = User.objects.create_user(username='reviewer_user', password='password123')
        self.leave_type = LeaveType.objects.create(
            name='Casual Leave',
            annual_quota=12,
            carry_forward=False,
            requires_medical_evidence=False
        )
        self.balance = LeaveBalance.objects.create(
            user=self.emp,
            leave_type=self.leave_type,
            total_days=12,
            consumed_days=0,
            pending_days=0
        )

    def test_01_leave_creation_and_balance_deduction(self):
        # 1. Employee applies for 3 days
        view_create = LeaveRequestViewSet.as_view({'post': 'create'})
        payload = {
            'leave_type': self.leave_type.id,
            'start_date': (date.today() + timedelta(days=2)).isoformat(),
            'end_date': (date.today() + timedelta(days=4)).isoformat(),
            'total_days': 3,
            'reason': 'Family function'
        }
        req = self.factory.post('/api/leave/', payload, format='json')
        force_authenticate(req, user=self.emp)
        resp = view_create(req)
        self.assertEqual(resp.status_code, 201)
        req_id = resp.data['id']

        # 2. Reviewer approves
        view_action = LeaveRequestViewSet.as_view({'post': 'action'})
        act_payload = {'action': 'approve', 'remarks': 'Approved'}
        act_req = self.factory.post(f'/api/leave/{req_id}/action/', act_payload, format='json')
        force_authenticate(act_req, user=self.reviewer)
        act_resp = view_action(act_req, pk=req_id)
        self.assertEqual(act_resp.status_code, 200)

        # 3. Assert balance and workflow record
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.consumed_days, Decimal('3.0'))
        history = LeaveWorkflowHistory.objects.filter(request_id=req_id).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.from_state, 'submitted')
        self.assertEqual(history.to_state, 'approved')
