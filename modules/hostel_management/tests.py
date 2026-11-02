import os
import sys
import unittest
from datetime import date

# Set up in-memory Django environment for standalone testing
if __name__ == "__main__" or "django" not in sys.modules:
    import django
    from django.conf import settings
    from django.core.management import call_command

    if not settings.configured:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)

        import types
        mod = types.ModuleType("hostel_management")
        mod.__path__ = [base_dir]
        mod.__file__ = os.path.join(base_dir, "__init__.py")
        sys.modules["hostel_management"] = mod

        settings.configure(
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "apps.HostelManagementConfig",
            ],
            TIME_ZONE="UTC",
            USE_TZ=True,
        )
        django.setup()
        call_command("migrate", run_syncdb=True, verbosity=0)

try:
    from hostel_management import services
    from hostel_management.models import (
        Hostel, Room, AccommodationRequest, AttendanceRecord,
        LeaveRequest, HostelComplaint, GuestRoomBooking,
        ExtendedStayRequest, HostelFine, HostelInventory,
        SecurityGuardShift, HostelNotice, Notification
    )
except ImportError:
    from . import services
    from .models import (
        Hostel, Room, AccommodationRequest, AttendanceRecord,
        LeaveRequest, HostelComplaint, GuestRoomBooking,
        ExtendedStayRequest, HostelFine, HostelInventory,
        SecurityGuardShift, HostelNotice, Notification
    )


class HostelManagementTests(unittest.TestCase):

    def setUp(self):
        Hostel.objects.all().delete()
        Notification.objects.all().delete()
        self.hostel = services.create_hostel("Aryabhatta Hostel", "ABH", total_capacity=50)
        self.room = services.create_room(self.hostel.id, "101", capacity=1)

    def test_01_hostel_master_and_role_binding(self):
        # UC-001, UC-002, UC-003, UC-004
        self.assertTrue(self.hostel.is_active)
        services.set_hostel_active(self.hostel.id, False)
        self.hostel.refresh_from_db()
        self.assertFalse(self.hostel.is_active)

        binding = services.assign_hostel_role(self.hostel.id, user_id=10, role="warden")
        self.assertEqual(binding.role, "warden")
        self.assertTrue(binding.is_active)

    def test_02_accommodation_request_and_capacity_enforcement(self):
        # UC-005, UC-006, BW-HM-01, BR-HM-010
        req = services.submit_accommodation_request(student_id=101, hostel_id=self.hostel.id)
        self.assertEqual(req.status, "submitted")

        allotted_req = services.allot_room(req.id, self.room.id, admin_id=1)
        self.assertEqual(allotted_req.status, "allotted")
        self.room.refresh_from_db()
        self.assertEqual(self.room.current_occupancy, 1)

        # Capacity limit enforcement: room is full (capacity=1)
        req2 = services.submit_accommodation_request(student_id=102, hostel_id=self.hostel.id)
        with self.assertRaises(ValueError):
            services.allot_room(req2.id, self.room.id, admin_id=1)

    def test_03_room_vacation_and_exchange(self):
        # UC-007, UC-010
        room2 = services.create_room(self.hostel.id, "102", capacity=2)
        success = services.exchange_rooms(101, self.room.id, 102, room2.id, caretaker_id=2)
        self.assertTrue(success)

        vacated = services.vacate_room(101, self.room.id, admin_id=1)
        self.assertEqual(vacated.current_occupancy, 0)

    def test_04_attendance_recording(self):
        # UC-012, UC-013, BR-HM-011
        rec = services.record_student_attendance(101, self.hostel.id, date.today(), "present", caretaker_id=2)
        self.assertEqual(rec.status, "present")
        records = services.get_student_attendance(101)
        self.assertEqual(records.count(), 1)

    def test_05_leave_request_and_review(self):
        # UC-014, UC-015, BW-HM-02, BW-HM-03, CW-HM-01
        lreq = services.submit_leave_request(101, self.hostel.id, date.today(), date.today(), "Family emergency")
        self.assertEqual(lreq.status, "submitted")

        approved = services.review_leave_request(lreq.id, "approved", caretaker_id=2, note="Granted")
        self.assertEqual(approved.status, "approved")

    def test_06_complaint_lifecycle_and_escalation(self):
        # UC-017, UC-018, BW-HM-04, BW-HM-05, CW-HM-02
        c = services.submit_hostel_complaint(101, self.hostel.id, "Plumbing", "Leaking faucet in washroom")
        self.assertEqual(c.status, "submitted")

        escalated = services.update_complaint_status(c.id, "escalated_to_warden", "Requires pipe replacement", 2)
        self.assertEqual(escalated.status, "escalated_to_warden")

    def test_07_guest_room_booking(self):
        # UC-020, UC-021, BW-HM-06, BW-HM-07, CW-HM-03
        booking = services.submit_guest_room_booking(101, self.hostel.id, "Parent", "G-1", date.today(), date.today())
        self.assertEqual(booking.status, "submitted")

        decision = services.review_guest_room_booking(booking.id, "approved", caretaker_id=2)
        self.assertEqual(decision.status, "approved")

    def test_08_extended_stay_and_compliance(self):
        # UC-023, UC-024, UC-025, BW-HM-08, BW-HM-09, CW-HM-04, BR-HM-020, BR-HM-021
        stay = services.submit_extended_stay_request(101, self.hostel.id, date.today(), date.today(), "Research project")
        self.assertEqual(stay.status, "submitted")

        services.record_extended_stay_compliance(stay.id, fee_amount=1500.0, payment_deadline=date.today(), compliance_status="compliant")
        stay.refresh_from_db()
        self.assertEqual(float(stay.fee_amount), 1500.0)
        self.assertEqual(stay.compliance_status, "compliant")

        reviewed = services.review_extended_stay_request(stay.id, "approved", warden_id=10)
        self.assertEqual(reviewed.status, "approved")

    def test_09_fine_management(self):
        # UC-026, BR-HM-025
        fine = services.record_hostel_fine(101, self.hostel.id, "Damaged notice board", 500.0, date.today(), caretaker_id=2)
        self.assertEqual(fine.amount, 500.0)

        # Missing required field should raise error
        with self.assertRaises(ValueError):
            services.record_hostel_fine(None, self.hostel.id, "", 0, None, 2)

    def test_10_inventory_and_logs(self):
        # UC-028, BR-HM-027
        item = services.update_hostel_inventory(self.hostel.id, "Study Chairs", 10, "added_stock", updater_id=2)
        self.assertEqual(item.quantity, 10)
        self.assertEqual(item.logs.count(), 1)

    def test_11_guard_shifts_and_notices(self):
        # UC-030, UC-031, UC-032
        shift = services.schedule_guard_shift(self.hostel.id, "Ramesh Kumar", "night", date.today(), warden_id=10)
        self.assertEqual(shift.guard_name, "Ramesh Kumar")

        notice = services.publish_hostel_notice(self.hostel.id, "Meeting", "Hostel meeting at 8 PM", 2, "caretaker")
        notices = services.get_hostel_notices(self.hostel.id)
        self.assertEqual(notices.count(), 1)

    def test_12_operational_report_and_notifications(self):
        # UC-033, UC-034, BR-HM-032, BR-HM-034
        services.send_notification(101, "info_alert", "Welcome to hostel.")
        report = services.generate_hostel_summary_report(self.hostel.id)
        self.assertEqual(report["hostel_code"], "ABH")
        self.assertIn("total_rooms", report)

        notifs = Notification.objects.filter(recipient_id=101)
        self.assertGreater(notifs.count(), 0)

    def test_13_api_views(self):
        from rest_framework.test import APIRequestFactory
        try:
            from hostel_management import views
        except ImportError:
            from . import views
        factory = APIRequestFactory()
        req = factory.get("/hostels/")
        resp = views.HostelListCreateView.as_view()(req)
        self.assertEqual(resp.status_code, 200)

        # Test creating hostel via API
        post_req = factory.post("/hostels/", {"name": "CV Raman", "code": "CVR", "total_capacity": 40}, format="json")
        post_resp = views.HostelListCreateView.as_view()(post_req)
        self.assertEqual(post_resp.status_code, 201)


if __name__ == "__main__":
    unittest.main()
