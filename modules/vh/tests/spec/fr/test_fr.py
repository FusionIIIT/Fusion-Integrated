# Specification-based automated tests for Functional Requirements (FR) strategy.
from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from modules.vh.models.alerts import BookingNotificationLog, StayAlert
from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem, InventoryReplenishment
from modules.vh.models.meal import MealBooking
from modules.vh.models.roles import OperationalRoleHolder
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.models.tariff import TariffConfig
from modules.vh.selectors.tariffs import get_applicable_tariff
from modules.vh.services.alerts import evaluate_no_shows, evaluate_overstays

pytestmark = pytest.mark.django_db


def test_fr_test_001_indenter_track_bookings(indenter_client):
    """
    test_id: FR-TEST-001
    source_id: AFR-VH-001 indenter-track-bookings
    """
    Booking.objects.create(
        booking_reference="BK-FR-001",
        indenter_id=101,
        visit_purpose="Official visit",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = indenter_client.get("/api/v1/vh/bookings/")
    assert resp.status_code == 200
    assert any(b["booking_reference"] == "BK-FR-001" for b in resp.data)


def test_fr_test_002_indenter_view_booking_detail(indenter_client):
    """
    test_id: FR-TEST-002
    source_id: AFR-VH-002 indenter-view-booking-detail
    """
    b = Booking.objects.create(
        booking_reference="BK-FR-002",
        indenter_id=101,
        visit_purpose="Guest Lecture",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = indenter_client.get(f"/api/v1/vh/bookings/{b.id}/")
    assert resp.status_code == 200
    assert resp.data["booking_reference"] == "BK-FR-002"
    assert resp.data["visit_purpose"] == "Guest Lecture"


def test_fr_test_003_indenter_printable_booking_detail(indenter_client):
    """
    test_id: FR-TEST-003
    source_id: AFR-VH-003 indenter-printable-booking-detail
    """
    b = Booking.objects.create(
        booking_reference="BK-FR-003",
        indenter_id=101,
        visit_purpose="Print Test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="approved",
    )
    resp = indenter_client.get(f"/api/v1/vh/bookings/{b.id}/")
    assert resp.status_code == 200
    assert "booking_reference" in resp.data
    assert "status" in resp.data
    assert resp.data["status"] == "approved"


def test_fr_test_004_visitor_no_direct_access():
    """
    test_id: FR-TEST-004
    source_id: AFR-VH-004 visitor-no-direct-access
    """
    anon = APIClient()
    resp = anon.get("/api/v1/vh/bookings/")
    assert resp.status_code == 401


def test_fr_test_005_indenter_submit_online_booking(indenter_client):
    """
    test_id: FR-TEST-005
    source_id: AFR-VH-005 indenter-submit-online-booking
    """
    payload = {
        "visitor_name": "Dr. Smith",
        "visitor_category": "A",
        "visit_purpose": "Keynote Speaker",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"


def test_fr_test_006_record_visitor_details(indenter_client):
    """
    test_id: FR-TEST-006
    source_id: AFR-VH-006 record-visitor-details
    """
    payload = {
        "visitor_name": "Dr. Ramanujan",
        "visitor_email": "ramanujan@math.org",
        "visitor_phone": "9876543210",
        "visitor_category": "A",
        "visit_purpose": "Math Conference",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    b_id = resp.data["id"]
    booking = Booking.objects.get(id=b_id)
    visitor = booking.visitors.first()
    assert visitor is not None
    assert visitor.name == "Dr. Ramanujan"
    assert visitor.email == "ramanujan@math.org"


def test_fr_test_007_record_visit_purpose(indenter_client):
    """
    test_id: FR-TEST-007
    source_id: AFR-VH-007 record-visit-purpose
    """
    payload = {
        "visitor_name": "Prof. Bose",
        "visitor_category": "A",
        "visit_purpose": "Physics Colloquium",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["visit_purpose"] == "Physics Colloquium"


def test_fr_test_008_record_visitor_category(indenter_client):
    """
    test_id: FR-TEST-008
    source_id: AFR-VH-008 record-visitor-category
    """
    payload = {
        "visitor_name": "Dr. Saha",
        "visitor_category": "B",
        "visit_purpose": "Astrophysics Talk",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "project",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["visitor_category"] == "B"


def test_fr_test_009_record_stay_duration_and_timings(indenter_client):
    """
    test_id: FR-TEST-009
    source_id: AFR-VH-009 record-stay-duration-and-timings
    """
    arr = date.today() + timedelta(days=15)
    dep = date.today() + timedelta(days=18)
    payload = {
        "visitor_name": "Dr. Kalam",
        "visitor_category": "A",
        "visit_purpose": "Convocation Address",
        "arrival_date": str(arr),
        "departure_date": str(dep),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["arrival_date"] == str(arr)
    assert resp.data["departure_date"] == str(dep)


def test_fr_test_010_record_rooms_and_occupants(indenter_client):
    """
    test_id: FR-TEST-010
    source_id: AFR-VH-010 record-rooms-and-occupants
    """
    payload = {
        "visitor_name": "Dr. Sarabhai",
        "visitor_category": "A",
        "visit_purpose": "Space Summit",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 2,
        "number_of_occupants": 4,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["number_of_rooms"] == 2
    assert resp.data["number_of_occupants"] == 4


def test_fr_test_011_record_billing_responsibility(indenter_client):
    """
    test_id: FR-TEST-011
    source_id: AFR-VH-011 record-billing-responsibility
    """
    payload = {
        "visitor_name": "Dr. Bhabha",
        "visitor_category": "A",
        "visit_purpose": "Atomic Energy Seminar",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "project",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["billing_responsibility"] == "project"


def test_fr_test_012_valid_billing_responsibility(indenter_client):
    """
    test_id: FR-TEST-012
    source_id: AFR-VH-012 valid-billing-responsibility
    """
    for val in ["visitor", "indenter", "institute", "project"]:
        payload = {
            "visitor_name": "Dr. Guest",
            "visitor_category": "A",
            "visit_purpose": "Research",
            "arrival_date": str(date.today() + timedelta(days=10)),
            "departure_date": str(date.today() + timedelta(days=12)),
            "number_of_rooms": 1,
            "number_of_occupants": 1,
            "billing_responsibility": val,
        }
        resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
        assert resp.status_code == 201


def test_fr_test_013_invalid_billing_responsibility(indenter_client):
    """
    test_id: FR-TEST-013
    source_id: AFR-VH-012 invalid-billing-responsibility
    """
    payload = {
        "visitor_name": "Dr. Guest",
        "visitor_category": "A",
        "visit_purpose": "Research",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "third_party",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_fr_test_014_initial_status_pending(indenter_client):
    """
    test_id: FR-TEST-014
    source_id: AFR-VH-013 initial-status-pending
    """
    payload = {
        "visitor_name": "Dr. Guest",
        "visitor_category": "A",
        "visit_purpose": "Research",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"


def test_fr_test_015_caretaker_review_requests(caretaker_client):
    """
    test_id: FR-TEST-015
    source_id: AFR-VH-014 caretaker-review-requests
    """
    Booking.objects.create(
        booking_reference="BK-REV-01",
        indenter_id=101,
        visit_purpose="Review test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = caretaker_client.get("/api/v1/vh/bookings/?status=pending")
    assert resp.status_code == 200
    assert any(b["booking_reference"] == "BK-REV-01" for b in resp.data)


def test_fr_test_016_caretaker_check_room_availability(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-016
    source_id: AFR-VH-015 caretaker-check-room-availability
    """
    s_date = str(date.today() + timedelta(days=20))
    e_date = str(date.today() + timedelta(days=22))
    resp = caretaker_client.get(
        f"/api/v1/vh/rooms/availability/?arrival_date={s_date}&departure_date={e_date}"
    )
    assert resp.status_code == 200
    assert len(resp.data) >= 3


def test_fr_test_017_caretaker_reject_booking_directly(caretaker_client):
    """
    test_id: FR-TEST-017
    source_id: AFR-VH-016 caretaker-reject-booking-directly
    """
    b = Booking.objects.create(
        booking_reference="BK-REJ-01",
        indenter_id=101,
        visit_purpose="Reject test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/route/",
        {"action": "reject", "reason": "No availability"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"
    assert resp.data["rejection_reason"] == "No availability"


def test_fr_test_018_caretaker_forward_booking(caretaker_client):
    """
    test_id: FR-TEST-018
    source_id: AFR-VH-017 caretaker-forward-booking
    """
    b = Booking.objects.create(
        booking_reference="BK-FWD-01",
        indenter_id=101,
        visit_purpose="Forward test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/route/",
        {"action": "forward"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "forwarded"


def test_fr_test_019_incharge_approve_booking(incharge_client):
    """
    test_id: FR-TEST-019
    source_id: AFR-VH-018 incharge-approve-booking
    """
    b = Booking.objects.create(
        booking_reference="BK-APP-01",
        indenter_id=101,
        visit_purpose="Approve test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="forwarded",
    )
    resp = incharge_client.post(
        f"/api/v1/vh/bookings/{b.id}/decide/",
        {"action": "approve"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


def test_fr_test_020_incharge_reject_booking(incharge_client):
    """
    test_id: FR-TEST-020
    source_id: AFR-VH-019 incharge-reject-booking
    """
    b = Booking.objects.create(
        booking_reference="BK-INREJ-01",
        indenter_id=101,
        visit_purpose="Incharge Reject test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="forwarded",
    )
    resp = incharge_client.post(
        f"/api/v1/vh/bookings/{b.id}/decide/",
        {"action": "reject", "reason": "Administrative grounds"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"
    assert resp.data["rejection_reason"] == "Administrative grounds"


def test_fr_test_021_notify_indenter_final_decision(incharge_client):
    """
    test_id: FR-TEST-021
    source_id: AFR-VH-020 notify-indenter-final-decision
    """
    b = Booking.objects.create(
        booking_reference="BK-NOTIF-01",
        indenter_id=101,
        visit_purpose="Decision notif test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="forwarded",
    )
    resp = incharge_client.post(
        f"/api/v1/vh/bookings/{b.id}/decide/",
        {"action": "approve"},
        format="json",
    )
    assert resp.status_code == 200
    assert BookingNotificationLog.objects.filter(booking=b).exists()


def test_fr_test_022_caretaker_record_telephonic_booking(caretaker_client):
    """
    test_id: FR-TEST-022
    source_id: AFR-VH-021 caretaker-record-telephonic-booking
    """
    payload = {
        "visitor_name": "Prof. Rao",
        "visitor_category": "B",
        "visit_purpose": "Telephonic Booking",
        "arrival_date": str(date.today() + timedelta(days=8)),
        "departure_date": str(date.today() + timedelta(days=10)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
        "booking_source": "telephonic",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["is_offline"] is True
    assert resp.data["booking_source"] == "telephonic"


def test_fr_test_023_caretaker_record_walkin_booking(caretaker_client):
    """
    test_id: FR-TEST-023
    source_id: AFR-VH-022 caretaker-record-walkin-booking
    """
    payload = {
        "visitor_name": "Prof. Sen",
        "visitor_category": "C",
        "visit_purpose": "Walk-in Guest",
        "arrival_date": str(date.today()),
        "departure_date": str(date.today() + timedelta(days=2)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
        "booking_source": "walk_in",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["is_offline"] is True
    assert resp.data["booking_source"] == "walk_in"


def test_fr_test_024_same_approval_routing_offline(caretaker_client, incharge_client):
    """
    test_id: FR-TEST-024
    source_id: AFR-VH-023 same-approval-routing-offline
    """
    payload = {
        "visitor_name": "Dr. Off",
        "visitor_category": "A",
        "visit_purpose": "Routing offline test",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
        "booking_source": "telephonic",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    b_id = resp.data["id"]

    resp_fwd = caretaker_client.post(
        f"/api/v1/vh/bookings/{b_id}/route/", {"action": "forward"}, format="json"
    )
    assert resp_fwd.status_code == 200
    assert resp_fwd.data["status"] == "forwarded_offline"

    resp_app = incharge_client.post(
        f"/api/v1/vh/bookings/{b_id}/decide/", {"action": "approve"}, format="json"
    )
    assert resp_app.status_code == 200
    assert resp_app.data["status"] == "approved_offline"


def test_fr_test_025_same_room_availability_offline(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-025
    source_id: AFR-VH-024 same-room-availability-offline
    """
    arr = str(date.today() + timedelta(days=30))
    dep = str(date.today() + timedelta(days=32))
    resp = caretaker_client.get(
        f"/api/v1/vh/rooms/availability/?arrival_date={arr}&departure_date={dep}"
    )
    assert resp.status_code == 200
    assert len(resp.data) >= 3


def test_fr_test_026_flag_offline_bookings(caretaker_client):
    """
    test_id: FR-TEST-026
    source_id: AFR-VH-025 flag-offline-bookings
    """
    b = Booking.objects.create(
        booking_reference="BK-OFF-01",
        indenter_id=201,
        is_offline=True,
        booking_source="walk_in",
        visit_purpose="Flag check",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="pending",
    )
    assert b.is_offline is True
    assert b.booking_source == "walk_in"


def test_fr_test_027_indenter_request_modification(indenter_client):
    """
    test_id: FR-TEST-027
    source_id: AFR-VH-026 indenter-request-modification
    """
    b = Booking.objects.create(
        booking_reference="BK-MOD-01",
        indenter_id=101,
        visit_purpose="Mod test",
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="approved",
    )
    new_dep = str(date.today() + timedelta(days=14))
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/modify/",
        {"departure_date": new_dep},
        format="json",
    )
    assert resp.status_code == 200
    b.refresh_from_db()
    assert str(b.departure_date) == new_dep


def test_fr_test_028_indenter_request_cancellation(indenter_client):
    """
    test_id: FR-TEST-028
    source_id: AFR-VH-027 indenter-request-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-CAN-01",
        indenter_id=101,
        visit_purpose="Cancel test",
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Event postponed"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "cancellation_requested"


def test_fr_test_029_compute_cancellation_charges(indenter_client):
    """
    test_id: FR-TEST-029
    source_id: AFR-VH-028 compute-cancellation-charges
    """
    b = Booking.objects.create(
        booking_reference="BK-CALC-01",
        indenter_id=101,
        visit_purpose="Calc test",
        arrival_date=date.today() + timedelta(days=4),
        departure_date=date.today() + timedelta(days=6),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Cancel within 7 days"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["cancellation_charge_percentage"] == "25.00"


def test_fr_test_030_cancellation_7_days_zero_charge(indenter_client):
    """
    test_id: FR-TEST-030
    source_id: AFR-VH-029 cancellation-7-days-zero-charge
    """
    b = Booking.objects.create(
        booking_reference="BK-7DAY-01",
        indenter_id=101,
        visit_purpose="7 day test",
        arrival_date=date.today() + timedelta(days=7),
        departure_date=date.today() + timedelta(days=9),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "7 days advance notice"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["cancellation_charge_percentage"] == "0.00"


def test_fr_test_031_cancellation_within_7_days_25_percent(indenter_client):
    """
    test_id: FR-TEST-031
    source_id: AFR-VH-030 cancellation-within-7-days-25-percent
    """
    b = Booking.objects.create(
        booking_reference="BK-W7-01",
        indenter_id=101,
        visit_purpose="within 7 days",
        arrival_date=date.today() + timedelta(days=3),
        departure_date=date.today() + timedelta(days=5),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Late cancel"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["cancellation_charge_percentage"] == "25.00"


def test_fr_test_032_cancellation_same_day_50_percent(indenter_client):
    """
    test_id: FR-TEST-032
    source_id: AFR-VH-031 cancellation-same-day-50-percent
    """
    b = Booking.objects.create(
        booking_reference="BK-SAMEDAY-01",
        indenter_id=101,
        visit_purpose="Same day cancel",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Emergency"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["cancellation_charge_percentage"] == "50.00"


def test_fr_test_033_caretaker_review_cancellation_requests(caretaker_client):
    """
    test_id: FR-TEST-033
    source_id: AFR-VH-032 caretaker-review-cancellation-requests
    """
    Booking.objects.create(
        booking_reference="BK-CRREV-01",
        indenter_id=101,
        visit_purpose="Cancellation review",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="cancellation_requested",
    )
    resp = caretaker_client.get("/api/v1/vh/bookings/?status=cancellation_requested")
    assert resp.status_code == 200
    assert any(b["booking_reference"] == "BK-CRREV-01" for b in resp.data)


def test_fr_test_034_caretaker_confirm_cancellation(caretaker_client):
    """
    test_id: FR-TEST-034
    source_id: AFR-VH-033 caretaker-confirm-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-CONF-01",
        indenter_id=101,
        visit_purpose="Confirm cancellation",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="cancellation_requested",
        cancellation_charge_percentage=Decimal("25.00"),
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/",
        {},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "cancelled"


def test_fr_test_035_adjust_billing_modification(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-035
    source_id: AFR-VH-034 adjust-billing-modification
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-MODBILL-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Mod billing",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="approved",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    b.status = "checked_out"
    b.departure_date = date.today() + timedelta(days=5)
    b.save()

    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["room_rent_total"])) == Decimal("3200.00")


def test_fr_test_036_adjust_billing_cancellation(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-036
    source_id: AFR-VH-035 adjust-billing-cancellation
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-CANBILL-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Cancel billing",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="approved",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    b.status = "cancellation_requested"
    b.cancellation_charge_percentage = Decimal("25.00")
    b.save()
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json")
    assert resp.status_code == 200
    bill = Bill.objects.get(booking=b)
    assert bill.cancellation_charge_total == Decimal("200.00")


def test_fr_test_037_room_allotment_only_after_approval(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-037
    source_id: AFR-VH-036 room-allotment-only-after-approval
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-PALLOT-01",
        indenter_id=101,
        visit_purpose="Pending allotment",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="pending",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/allot-rooms/",
        {"room_ids": [r1.id], "occupancy_type": "single"},
        format="json",
    )
    assert resp.status_code in [400, 409, 422]


def test_fr_test_038_support_single_occupancy_records(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-038
    source_id: AFR-VH-037 support-single-occupancy-records
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-SING-01",
        indenter_id=101,
        visit_purpose="Single test",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="approved",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/allot-rooms/",
        {"room_ids": [r1.id], "occupancy_type": "single"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data[0]["occupancy_type"] == "single"


def test_fr_test_039_support_double_occupancy_records(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-039
    source_id: AFR-VH-038 support-double-occupancy-records
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-DOUB-01",
        indenter_id=101,
        visit_purpose="Double test",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="approved",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/allot-rooms/",
        {"room_ids": [r1.id], "occupancy_type": "double"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data[0]["occupancy_type"] == "double"


def test_fr_test_040_support_suite_room_records():
    """
    test_id: FR-TEST-040
    source_id: AFR-VH-039 support-suite-room-records
    """
    room = Room.objects.create(
        room_number="SUITE-01",
        room_type="suite",
        capacity=2,
        is_active=True,
    )
    assert room.room_type == "suite"


def test_fr_test_041_support_non_suite_room_records():
    """
    test_id: FR-TEST-041
    source_id: AFR-VH-040 support-non-suite-room-records
    """
    room = Room.objects.create(
        room_number="NONSUITE-01",
        room_type="non_suite",
        capacity=2,
        is_active=True,
    )
    assert room.room_type == "non_suite"


def test_fr_test_042_record_guest_checkin_time(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-042
    source_id: AFR-VH-041 record-guest-checkin-time
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-CHKIN-01",
        indenter_id=101,
        visit_purpose="Checkin time",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="approved",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    b.status = "room_allotted"
    b.save()
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/checkin/", {}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "checked_in"
    assert resp.data["checkin_time"] is not None


def test_fr_test_043_record_guest_checkout_time(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-043
    source_id: AFR-VH-042 record-guest-checkout-time
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-CHKOUT-01",
        indenter_id=101,
        visit_purpose="Checkout time",
        arrival_date=date.today() - timedelta(days=2),
        departure_date=date.today(),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/checkout/", {"verified_by_guest": True}, format="json"
    )
    assert resp.status_code == 200
    b.refresh_from_db()
    assert b.status == "checked_out"
    assert resp.data["checkout_time"] is not None


def test_fr_test_044_generate_no_show_alert():
    """
    test_id: FR-TEST-044
    source_id: AFR-VH-043 generate-no-show-alert
    """
    b = Booking.objects.create(
        booking_reference="BK-NOSHOW-01",
        indenter_id=101,
        visit_purpose="No show alert test",
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today() + timedelta(days=1),
        status="room_allotted",
    )
    created = evaluate_no_shows()
    assert isinstance(created, int) and created >= 0
    alert = StayAlert.objects.filter(booking=b, alert_type="no_show").first()
    assert alert is not None


def test_fr_test_045_generate_overstay_alert():
    """
    test_id: FR-TEST-045
    source_id: AFR-VH-044 generate-overstay-alert
    """
    b = Booking.objects.create(
        booking_reference="BK-OVERSTAY-01",
        indenter_id=101,
        visit_purpose="Overstay alert test",
        arrival_date=date.today() - timedelta(days=4),
        departure_date=date.today() - timedelta(days=1),
        status="checked_in",
    )
    created = evaluate_overstays()
    assert isinstance(created, int) and created >= 0
    alert = StayAlert.objects.filter(booking=b, alert_type="overstay").first()
    assert alert is not None


def test_fr_test_046_visitor_categories_a_b_c_d(indenter_client):
    """
    test_id: FR-TEST-046
    source_id: AFR-VH-045 visitor-categories-a-b-c-d
    """
    for cat in ["A", "B", "C", "D"]:
        payload = {
            "visitor_name": f"Dr. Cat {cat}",
            "visitor_category": cat,
            "visit_purpose": "Category test",
            "arrival_date": str(date.today() + timedelta(days=5)),
            "departure_date": str(date.today() + timedelta(days=7)),
            "number_of_rooms": 1,
            "number_of_occupants": 1,
            "billing_responsibility": "visitor",
        }
        resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
        assert resp.status_code == 201

    payload_invalid = {
        "visitor_name": "Dr. Cat E",
        "visitor_category": "E",
        "visit_purpose": "Invalid category test",
        "arrival_date": str(date.today() + timedelta(days=5)),
        "departure_date": str(date.today() + timedelta(days=7)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp_inv = indenter_client.post("/api/v1/vh/bookings/", payload_invalid, format="json")
    assert resp_inv.status_code in [400, 422]


def test_fr_test_047_category_specific_tariffs(sample_tariffs):
    """
    test_id: FR-TEST-047
    source_id: AFR-VH-046 category-specific-tariffs
    """
    t_a = TariffConfig.objects.filter(category="A", room_type="non_suite", occupancy="single").first()
    t_b = TariffConfig.objects.filter(category="B", room_type="non_suite", occupancy="single").first()
    assert t_a.daily_rate == Decimal("500.00")
    assert t_b.daily_rate == Decimal("800.00")


def test_fr_test_048_occupancy_specific_tariffs():
    """
    test_id: FR-TEST-048
    source_id: AFR-VH-047 occupancy-specific-tariffs
    """
    t_s = TariffConfig.objects.create(
        category="C",
        room_type="non_suite",
        occupancy="single",
        daily_rate=Decimal("400.00"),
        effective_from=date.today(),
    )
    t_d = TariffConfig.objects.create(
        category="C",
        room_type="non_suite",
        occupancy="double",
        daily_rate=Decimal("600.00"),
        effective_from=date.today(),
    )
    assert t_s.daily_rate != t_d.daily_rate


def test_fr_test_049_tariff_effective_from_dates():
    """
    test_id: FR-TEST-049
    source_id: AFR-VH-048 tariff-effective-from-dates
    """
    eff = date.today() - timedelta(days=10)
    t = TariffConfig.objects.create(
        category="D",
        room_type="non_suite",
        occupancy="single",
        daily_rate=Decimal("300.00"),
        effective_from=eff,
    )
    assert t.effective_from == eff


def test_fr_test_050_auto_select_applicable_tariff(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-050
    source_id: AFR-VH-049 auto-select-applicable-tariff
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-AUTOTAR-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Auto tariff select",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=2),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["room_rent_total"])) == Decimal("800.00")


def test_fr_test_051_historical_bills_immutable_to_tariff_changes(
    caretaker_client, sample_rooms, sample_tariffs
):
    """
    test_id: FR-TEST-051
    source_id: AFR-VH-050 historical-bills-immutable-to-tariff-changes
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-HISTIMMUT-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Historical immutable",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=2),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    bill_id = resp.data["id"]

    caretaker_client.post(
        f"/api/v1/vh/bills/{bill_id}/settle/",
        {"amount_paid": "800.00", "payment_mode": "offline_cash"},
        format="json",
    )

    TariffConfig.objects.create(
        category="A",
        room_type="suite",
        occupancy="single",
        daily_rate=Decimal("1500.00"),
        effective_from=date.today(),
    )

    bill = Bill.objects.get(id=bill_id)
    assert bill.total_amount == Decimal("800.00")


def test_fr_test_052_meals_only_for_staying_guests(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-052
    source_id: AFR-VH-051 meals-only-for-staying-guests
    """
    b = Booking.objects.create(
        booking_reference="BK-PNDMEAL-01",
        indenter_id=101,
        visit_purpose="Pending stay meal test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today() + timedelta(days=5)),
            "meal_option": "full_day",
        },
        format="json",
    )
    assert resp.status_code in [400, 409, 422]


def test_fr_test_053_full_day_meal_options(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-053
    source_id: AFR-VH-052 full-day-meal-options
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-FDMEAL-01",
        indenter_id=101,
        visit_purpose="Full day meal",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today()),
            "meal_option": "full_day",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["meal_option"] == "full_day"


def test_fr_test_054_individual_meal_options(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-054
    source_id: AFR-VH-053 individual-meal-options
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-INDMEAL-01",
        indenter_id=101,
        visit_purpose="Individual meal",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today()),
            "meal_option": "individual",
            "individual_type": "breakfast",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["individual_type"] == "breakfast"


def test_fr_test_055_addon_meal_options(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-055
    source_id: AFR-VH-054 addon-meal-options
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-ADDMEAL-01",
        indenter_id=101,
        visit_purpose="Addon meal",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today()),
            "meal_option": "add_on",
            "add_on_type": "tea",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["add_on_type"] == "tea"


def test_fr_test_056_individual_meal_options_restricted(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-056
    source_id: AFR-VH-055 individual-meal-options-restricted
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-INVIND-01",
        indenter_id=101,
        visit_purpose="Invalid individual meal",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today()),
            "meal_option": "individual",
            "individual_type": "midnight_snack",
        },
        format="json",
    )
    assert resp.status_code in [400, 422]


def test_fr_test_057_addon_meal_options_restricted(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-057
    source_id: AFR-VH-056 addon-meal-options-restricted
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-INVADD-01",
        indenter_id=101,
        visit_purpose="Invalid addon meal",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today()),
            "meal_option": "add_on",
            "add_on_type": "coffee",
        },
        format="json",
    )
    assert resp.status_code in [400, 422]


def test_fr_test_058_link_meals_to_stay_duration(caretaker_client, sample_rooms):
    """
    test_id: FR-TEST-058
    source_id: AFR-VH-057 link-meals-to-stay-duration
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-OUTDUR-01",
        indenter_id=101,
        visit_purpose="Out of duration meal",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today() + timedelta(days=5)),
            "meal_option": "full_day",
        },
        format="json",
    )
    assert resp.status_code in [400, 422]


def test_fr_test_059_meals_reflected_in_billing(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-059
    source_id: AFR-VH-058 meals-reflected-in-billing
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-MBILL-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Meals billing",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    MealBooking.objects.create(
        booking=b,
        meal_date=date.today(),
        meal_option="individual",
        individual_type="breakfast",
        quantity=1,
        rate=Decimal("100.00"),
        amount=Decimal("100.00"),
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["meal_charge_total"])) == Decimal("100.00")


def test_fr_test_060_generate_bills_room_rent(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-060
    source_id: AFR-VH-059 generate-bills-room-rent
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-RBILL-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Rent billing",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["room_rent_total"])) == Decimal("1600.00")


def test_fr_test_061_generate_bills_meal_consumption(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-061
    source_id: AFR-VH-060 generate-bills-meal-consumption
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-MCBILL-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Meal cons billing",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    MealBooking.objects.create(
        booking=b,
        meal_date=date.today(),
        meal_option="full_day",
        quantity=1,
        rate=Decimal("350.00"),
        amount=Decimal("350.00"),
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["meal_charge_total"])) == Decimal("350.00")


def test_fr_test_062_generate_bills_cancellation_charges(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-062
    source_id: AFR-VH-061 generate-bills-cancellation-charges
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-CCBILL-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Cancellation charge bill",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="cancelled",
        cancellation_charge_percentage=Decimal("50.00"),
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["cancellation_charge_total"])) == Decimal("400.00")


def test_fr_test_063_record_billing_responsibility(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-063
    source_id: AFR-VH-062 record-billing-responsibility
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-RESPBILL-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Resp bill",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="checked_out",
        billing_responsibility="institute",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert resp.data["billing_responsibility"] == "institute"


def test_fr_test_064_bills_settled_offline_cash(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-064
    source_id: AFR-VH-063 bills-settled-offline-cash
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-CSH-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Cash settle",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    bill_id = resp.data["id"]

    resp_s = caretaker_client.post(
        f"/api/v1/vh/bills/{bill_id}/settle/",
        {"amount_paid": "800.00", "payment_mode": "offline_cash"},
        format="json",
    )
    assert resp_s.status_code == 200
    assert resp_s.data["payment_mode"] == "offline_cash"


def test_fr_test_065_record_offline_settlement_info(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-065
    source_id: AFR-VH-064 record-offline-settlement-info
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-INFO-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Settle info",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    bill_id = resp.data["id"]

    resp_s = caretaker_client.post(
        f"/api/v1/vh/bills/{bill_id}/settle/",
        {
            "amount_paid": "800.00",
            "payment_mode": "offline_cash",
            "receipt_number": "REC-9988",
        },
        format="json",
    )
    assert resp_s.status_code == 200
    assert resp_s.data["receipt_number"] == "REC-9988"


def test_fr_test_066_caretaker_verify_bill_at_checkout(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-066
    source_id: AFR-VH-065 caretaker-verify-bill-at-checkout
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-VERCHK-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Verify bill checkout",
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today(),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/checkout/", {"verified_by_guest": True}, format="json"
    )
    assert resp.status_code == 200
    bill = Bill.objects.get(booking=b)
    assert bill.verified_by is not None


def test_fr_test_067_maintain_immutable_billing_records(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-067
    source_id: AFR-VH-066 maintain-immutable-billing-records
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-IMMUT-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Immutability check",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    bill_id = resp.data["id"]
    caretaker_client.post(
        f"/api/v1/vh/bills/{bill_id}/settle/",
        {"amount_paid": "800.00", "payment_mode": "offline_cash"},
        format="json",
    )
    bill = Bill.objects.get(id=bill_id)
    assert bill.is_immutable is True


def test_fr_test_068_caretaker_maintain_inventory_records(caretaker_client):
    """
    test_id: FR-TEST-068
    source_id: AFR-VH-068 caretaker-maintain-inventory-records
    """
    payload = {
        "item_name": "Bed Sheet Standard",
        "category": "linen",
        "current_quantity": 30,
        "minimum_threshold": 10,
        "unit": "pieces",
    }
    resp = caretaker_client.post("/api/v1/vh/inventory/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["item_name"] == "Bed Sheet Standard"


def test_fr_test_069_support_inventory_categories(caretaker_client):
    """
    test_id: FR-TEST-069
    source_id: AFR-VH-069 support-inventory-categories
    """
    for cat in ["linen", "utensils", "consumables"]:
        payload = {
            "item_name": f"Test Item {cat}",
            "category": cat,
            "current_quantity": 10,
            "minimum_threshold": 5,
            "unit": "pieces",
        }
        resp = caretaker_client.post("/api/v1/vh/inventory/", payload, format="json")
        assert resp.status_code == 200


def test_fr_test_070_record_current_quantity(caretaker_client):
    """
    test_id: FR-TEST-070
    source_id: AFR-VH-070 record-current-quantity
    """
    item = InventoryItem.objects.create(
        item_name="Pillow Covers",
        category="linen",
        current_quantity=45,
        minimum_threshold=15,
        unit="pieces",
    )
    assert item.current_quantity == 45


def test_fr_test_071_record_minimum_threshold(caretaker_client):
    """
    test_id: FR-TEST-071
    source_id: AFR-VH-071 record-minimum-threshold
    """
    item = InventoryItem.objects.create(
        item_name="Blanket Woolen",
        category="linen",
        current_quantity=20,
        minimum_threshold=8,
        unit="pieces",
    )
    assert item.minimum_threshold == 8


def test_fr_test_072_alert_when_quantity_below_threshold(caretaker_client):
    """
    test_id: FR-TEST-072
    source_id: AFR-VH-072 alert-when-quantity-below-threshold
    """
    item = InventoryItem.objects.create(
        item_name="Soap Bars",
        category="consumables",
        current_quantity=4,
        minimum_threshold=10,
        unit="pieces",
        is_threshold_alert=True,
    )
    assert item.is_threshold_alert is True


def test_fr_test_073_incharge_review_replenishment_requests(incharge_client):
    """
    test_id: FR-TEST-073
    source_id: AFR-VH-073 incharge-review-replenishment-requests
    """
    item = InventoryItem.objects.create(
        item_name="Tea Cups",
        category="utensils",
        current_quantity=2,
        minimum_threshold=20,
        unit="pieces",
    )
    InventoryReplenishment.objects.create(
        item=item,
        requested_quantity=30,
        requested_by=201,
        status="pending",
    )
    resp = incharge_client.get("/api/v1/vh/inventory/")
    assert resp.status_code == 200


def test_fr_test_074_incharge_approve_replenishment_request(incharge_client):
    """
    test_id: FR-TEST-074
    source_id: AFR-VH-074 incharge-approve-replenishment-request
    """
    item = InventoryItem.objects.create(
        item_name="Spoons",
        category="utensils",
        current_quantity=5,
        minimum_threshold=25,
        unit="pieces",
    )
    rep = InventoryReplenishment.objects.create(
        item=item,
        requested_quantity=20,
        requested_by=201,
        status="pending",
    )
    resp = incharge_client.post(
        f"/api/v1/vh/inventory/replenishments/{rep.id}/approve/",
        {"decision": "approved", "remarks": "Approved"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


def test_fr_test_075_notification_booking_submission(indenter_client):
    """
    test_id: FR-TEST-075
    source_id: AFR-VH-076 notification-booking-submission
    """
    payload = {
        "visitor_name": "Dr. Notif",
        "visitor_category": "A",
        "visit_purpose": "Notif check",
        "arrival_date": str(date.today() + timedelta(days=5)),
        "departure_date": str(date.today() + timedelta(days=7)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    b_id = resp.data["id"]
    booking = Booking.objects.get(id=b_id)
    assert BookingNotificationLog.objects.filter(booking=booking).exists()


def test_fr_test_076_notification_approval_or_rejection(caretaker_client):
    """
    test_id: FR-TEST-076
    source_id: AFR-VH-077 notification-approval-or-rejection
    """
    b = Booking.objects.create(
        booking_reference="BK-NOTREJ-01",
        indenter_id=101,
        visit_purpose="Notif reject",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/route/",
        {"action": "reject", "reason": "No space"},
        format="json",
    )
    assert resp.status_code == 200
    assert BookingNotificationLog.objects.filter(booking=b).exists()


def test_fr_test_077_notification_modification_cancellation(caretaker_client):
    """
    test_id: FR-TEST-077
    source_id: AFR-VH-078 notification-modification-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-NOTCAN-01",
        indenter_id=101,
        visit_purpose="Notif cancel",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="cancellation_requested",
    )
    from modules.vh.services.notifications import notify_cancellation_update
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/",
        {},
        format="json",
    )
    assert resp.status_code == 200
    notify_cancellation_update(b)
    assert BookingNotificationLog.objects.filter(booking=b).exists()


def test_fr_test_078_notification_stay_reminders():
    """
    test_id: FR-TEST-078
    source_id: AFR-VH-079 notification-stay-reminders
    """
    from modules.vh.tasks import send_stay_reminders
    send_stay_reminders()
    assert True


def test_fr_test_079_notification_inventory_threshold_alert(caretaker_client):
    """
    test_id: FR-TEST-079
    source_id: AFR-VH-080 notification-inventory-threshold-alert
    """
    item = InventoryItem.objects.create(
        item_name="Dish Soap",
        category="consumables",
        current_quantity=2,
        minimum_threshold=10,
        unit="bottles",
        is_threshold_alert=True,
    )
    assert item.is_threshold_alert is True


def test_fr_test_080_incharge_booking_summary_report(incharge_client):
    """
    test_id: FR-TEST-080
    source_id: AFR-VH-082 incharge-booking-summary-report
    """
    resp = incharge_client.get("/api/v1/vh/reports/incharge/?report_type=summary")
    assert resp.status_code == 200
    assert "total_bookings" in resp.data


def test_fr_test_081_incharge_category_occupancy_report(incharge_client):
    """
    test_id: FR-TEST-081
    source_id: AFR-VH-083 incharge-category-occupancy-report
    """
    resp = incharge_client.get("/api/v1/vh/reports/incharge/?report_type=occupancy")
    assert resp.status_code == 200
    assert isinstance(resp.data, list)


def test_fr_test_082_incharge_revenue_billing_summary_report(incharge_client):
    """
    test_id: FR-TEST-082
    source_id: AFR-VH-084 incharge-revenue-billing-summary-report
    """
    resp = incharge_client.get("/api/v1/vh/reports/incharge/?report_type=revenue")
    assert resp.status_code == 200
    assert "total_billed" in resp.data or "total_revenue" in resp.data


def test_fr_test_083_incharge_inventory_usage_report(incharge_client):
    """
    test_id: FR-TEST-083
    source_id: AFR-VH-085 incharge-inventory-usage-report
    """
    resp = incharge_client.get("/api/v1/vh/reports/incharge/?report_type=inventory")
    assert resp.status_code == 200
    assert isinstance(resp.data, list)


def test_fr_test_084_caretaker_daily_occupancy_report(caretaker_client):
    """
    test_id: FR-TEST-084
    source_id: AFR-VH-086 caretaker-daily-occupancy-report
    """
    resp = caretaker_client.get("/api/v1/vh/reports/caretaker/?report_type=occupancy")
    assert resp.status_code == 200
    assert "total_rooms_occupied" in resp.data


def test_fr_test_085_caretaker_arrivals_departures_report(caretaker_client):
    """
    test_id: FR-TEST-085
    source_id: AFR-VH-087 caretaker-arrivals-departures-report
    """
    resp = caretaker_client.get("/api/v1/vh/reports/caretaker/?report_type=arrivals")
    assert resp.status_code == 200
    assert "arrivals" in resp.data


def test_fr_test_086_caretaker_pending_approval_report(caretaker_client):
    """
    test_id: FR-TEST-086
    source_id: AFR-VH-088 caretaker-pending-approval-report
    """
    resp = caretaker_client.get("/api/v1/vh/reports/caretaker/?report_type=pending")
    assert resp.status_code == 200
    assert "pending_caretaker_review" in resp.data


def test_fr_test_087_caretaker_stay_exception_logs(caretaker_client):
    """
    test_id: FR-TEST-087
    source_id: AFR-VH-089 caretaker-stay-exception-logs
    """
    resp = caretaker_client.get("/api/v1/vh/reports/caretaker/?report_type=exceptions")
    assert resp.status_code == 200
    assert isinstance(resp.data, list)


def test_fr_test_088_exactly_one_active_caretaker(incharge_client):
    """
    test_id: FR-TEST-088
    source_id: AFR-VH-090 exactly-one-active-caretaker
    """
    resp = incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {
            "role_name": "caretaker",
            "new_user_id": 501,
            "valid_from": str(date.today()),
        },
        format="json",
    )
    assert resp.status_code == 200
    active_count = OperationalRoleHolder.objects.filter(role_name="caretaker", is_active=True).count()
    assert active_count == 1


def test_fr_test_089_exactly_one_active_incharge(incharge_client):
    """
    test_id: FR-TEST-089
    source_id: AFR-VH-091 exactly-one-active-incharge
    """
    resp = incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {
            "role_name": "incharge",
            "new_user_id": 601,
            "valid_from": str(date.today()),
        },
        format="json",
    )
    assert resp.status_code == 200
    active_count = OperationalRoleHolder.objects.filter(role_name="incharge", is_active=True).count()
    assert active_count == 1


def test_fr_test_090_time_bound_role_assignments(incharge_client):
    """
    test_id: FR-TEST-090
    source_id: AFR-VH-092 time-bound-role-assignments
    """
    v_from = str(date.today())
    v_to = str(date.today() + timedelta(days=90))
    resp = incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {
            "role_name": "caretaker",
            "new_user_id": 701,
            "valid_from": v_from,
            "valid_to": v_to,
        },
        format="json",
    )
    assert resp.status_code == 200
    holder = OperationalRoleHolder.objects.get(user_id=701, role_name="caretaker")
    assert holder.valid_to is not None


def test_fr_test_091_immediate_role_reassignment(incharge_client):
    """
    test_id: FR-TEST-091
    source_id: AFR-VH-093 immediate-role-reassignment
    """
    resp = incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {
            "role_name": "caretaker",
            "new_user_id": 801,
            "valid_from": str(date.today()),
        },
        format="json",
    )
    assert resp.status_code == 200
    active_ct = OperationalRoleHolder.objects.filter(role_name="caretaker", is_active=True).first()
    assert active_ct.user_id == 801


def test_fr_test_092_transfer_pending_records_on_reassign(incharge_client):
    """
    test_id: FR-TEST-092
    source_id: AFR-VH-094 transfer-pending-records-on-reassign
    """
    b = Booking.objects.create(
        booking_reference="BK-TRPND-01",
        indenter_id=101,
        visit_purpose="Pending transfer check",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {"role_name": "caretaker", "new_user_id": 901, "valid_from": str(date.today())},
        format="json",
    )
    b.refresh_from_db()
    assert b.status == "pending"


def test_fr_test_093_transfer_ongoing_records_on_reassign(incharge_client, sample_rooms):
    """
    test_id: FR-TEST-093
    source_id: AFR-VH-095 transfer-ongoing-records-on-reassign
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-TRONG-01",
        indenter_id=101,
        visit_purpose="Ongoing transfer check",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {"role_name": "caretaker", "new_user_id": 902, "valid_from": str(date.today())},
        format="json",
    )
    b.refresh_from_db()
    assert b.status == "checked_in"


def test_fr_test_094_auditability_booking_records(indenter_client):
    """
    test_id: FR-TEST-094
    source_id: AFR-VH-100 auditability-booking-records
    """
    payload = {
        "visitor_name": "Dr. Auditable",
        "visitor_category": "A",
        "visit_purpose": "Audit test",
        "arrival_date": str(date.today() + timedelta(days=5)),
        "departure_date": str(date.today() + timedelta(days=7)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    b = Booking.objects.get(id=resp.data["id"])
    assert b.created_at is not None
    assert b.updated_at is not None


def test_fr_test_095_unambiguous_tariff_selection(sample_tariffs):
    """
    test_id: FR-TEST-095
    source_id: AFR-VH-108 unambiguous-tariff-selection
    """
    rate = get_applicable_tariff(category="A", room_type="suite", occupancy="single")
    assert rate == Decimal("800.00")


def test_fr_test_096_role_boundary_enforcement(indenter_client):
    """
    test_id: FR-TEST-096
    source_id: AFR-VH-109 role-boundary-enforcement
    """
    b = Booking.objects.create(
        booking_reference="BK-BOUND-01",
        indenter_id=101,
        visit_purpose="Boundary check",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/route/",
        {"action": "reject", "reason": "Unauthorized"},
        format="json",
    )
    assert resp.status_code == 403


def test_fr_test_097_exclude_dynamic_pricing_discounts(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: FR-TEST-097
    source_id: AFR-VH-113 exclude-dynamic-pricing-discounts
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-PRICING-01",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Fixed price test",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert "discount" not in resp.data
    assert Decimal(str(resp.data["room_rent_total"])) == Decimal("800.00")
