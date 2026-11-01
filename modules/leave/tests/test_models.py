# tests/test_models.py

from django.test import TestCase
from modules.leave.models import LeaveRequest
from modules.leave.services import create_leave_request, update_leave_request, delete_leave_request

class LeaveRequestModelTest(TestCase):
    def test_str(self):
        request = LeaveRequest.objects.create(
            user=self.user,
            start_date="2026-11-15",
            end_date="2026-11-20",
            reason="Family emergency",
            status="PENDING"
        )
        self.assertEqual(str(request), f"LeaveRequest {request.id}")

    def test_permissions(self):
        user = self.user
        request = create_leave_request(user, "2026-11-15", "2026-11-20", "Family emergency")
        self.assertEqual(request.status, "PENDING")
        
        update_leave_request(request.id, user, status="APPROVED")
        request.refresh_from_db()
        self.assertEqual(request.status, "APPROVED")
        
        delete_leave_request(request.id, user)
        self.assertFalse(LeaveRequest.objects.filter(id=request.id).exists())
