# tests/test_services.py

from django.test import TestCase
from modules.leave.models import LeaveRequest
from modules.leave.services import create_leave_request, update_leave_request, delete_leave_request

class LeaveRequestServiceTest(TestCase):
    def test_create_request(self):
        user = self.user
        request = create_leave_request(user, "2026-11-15", "2026-11-20", "Family emergency")
        self.assertEqual(request.status, "PENDING")
        self.assertEqual(request.user, user)

    def test_update_request(self):
        user = self.user
        request = create_leave_request(user, "2026-11-15", "2026-11-20", "Family emergency")
        update_leave_request(request.id, user, status="APPROVED")
        request.refresh_from_db()
        self.assertEqual(request.status, "APPROVED")

    def test_delete_request(self):
        user = self.user
        request = create_leave_request(user, "2026-11-15", "2026-11-20", "Family emergency")
        delete_leave_request(request.id, user)
        self.assertFalse(LeaveRequest.objects.filter(id=request.id).exists())
