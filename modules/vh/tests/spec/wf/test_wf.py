# Specification-based automated tests for Workflows (WF) strategy.
# Covers all business workflows BW-VH-01 through BW-VH-10 and composite workflows CW-VH-01..02.
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.room import RoomAllotment

pytestmark = pytest.mark.django_db


def test_wf_test_001_bw01_s1_submission_accepted(indenter_client):
    """
    test_id: WF-TEST-001
    source_id: BW-VH-01 S1 submission-accepted
    """
    payload = {
        "visitor_name": "Prof. Turing",
        "visitor_category": "A",
        "visit_purpose": "Guest Lecture",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"


def test_wf_test_002_bw01_s2_caretaker_reject(caretaker_client):
    """
    test_id: WF-TEST-002
    source_id: BW-VH-01 S2 caretaker-reject
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-002",
        indenter_id=101,
        visit_purpose="Workshop",
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="pending",
    )
    payload = {"action": "reject", "reason": "No capacity for workshop"}
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/route/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"
    assert resp.data["rejection_reason"] == "No capacity for workshop"


def test_wf_test_003_bw02_s1_submission_accepted(indenter_client):
    """
    test_id: WF-TEST-003
    source_id: BW-VH-02 S1 submission-accepted
    """
    payload = {
        "visitor_name": "Dr. Lovelace",
        "visitor_category": "B",
        "visit_purpose": "Keynote Lecture",
        "arrival_date": str(date.today() + timedelta(days=14)),
        "departure_date": str(date.today() + timedelta(days=16)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"


def test_wf_test_004_bw02_s2_caretaker_forward(caretaker_client):
    """
    test_id: WF-TEST-004
    source_id: BW-VH-02 S2 caretaker-forward
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-004",
        indenter_id=101,
        visit_purpose="Keynote Lecture",
        arrival_date=date.today() + timedelta(days=14),
        departure_date=date.today() + timedelta(days=16),
        status="pending",
    )
    payload = {"action": "forward", "reason": "Recommended for approval"}
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/route/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "forwarded"


def test_wf_test_005_bw02_s3_incharge_approve(incharge_client):
    """
    test_id: WF-TEST-005
    source_id: BW-VH-02 S3 incharge-approve
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-005",
        indenter_id=101,
        visit_purpose="Keynote Lecture",
        arrival_date=date.today() + timedelta(days=14),
        departure_date=date.today() + timedelta(days=16),
        status="forwarded",
    )
    payload = {"action": "approve", "reason": "Approved as institute guest"}
    resp = incharge_client.post(f"/api/v1/vh/bookings/{b.id}/decide/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


def test_wf_test_006_bw03_s1_submission_accepted(indenter_client):
    """
    test_id: WF-TEST-006
    source_id: BW-VH-03 S1 submission-accepted
    """
    payload = {
        "visitor_name": "Dr. Shannon",
        "visitor_category": "C",
        "visit_purpose": "Seminar",
        "arrival_date": str(date.today() + timedelta(days=8)),
        "departure_date": str(date.today() + timedelta(days=10)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "project",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"


def test_wf_test_007_bw03_s2_caretaker_forward(caretaker_client):
    """
    test_id: WF-TEST-007
    source_id: BW-VH-03 S2 caretaker-forward
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-007",
        indenter_id=101,
        visit_purpose="Seminar",
        arrival_date=date.today() + timedelta(days=8),
        departure_date=date.today() + timedelta(days=10),
        status="pending",
    )
    payload = {"action": "forward"}
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/route/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "forwarded"


def test_wf_test_008_bw03_s3_incharge_reject(incharge_client):
    """
    test_id: WF-TEST-008
    source_id: BW-VH-03 S3 incharge-reject
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-008",
        indenter_id=101,
        visit_purpose="Seminar",
        arrival_date=date.today() + timedelta(days=8),
        departure_date=date.today() + timedelta(days=10),
        status="forwarded",
    )
    payload = {"action": "reject", "reason": "Ineligible purpose"}
    resp = incharge_client.post(f"/api/v1/vh/bookings/{b.id}/decide/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"
    assert resp.data["rejection_reason"] == "Ineligible purpose"


def test_wf_test_009_bw04_s1_offline_recorded(caretaker_client):
    """
    test_id: WF-TEST-009
    source_id: BW-VH-04 S1 offline-recorded
    """
    payload = {
        "booking_source": "telephonic",
        "visitor_name": "Telephonic Guest",
        "visitor_category": "A",
        "visit_purpose": "Emergency Meeting",
        "arrival_date": str(date.today() + timedelta(days=3)),
        "departure_date": str(date.today() + timedelta(days=5)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending_offline"
    assert resp.data["is_offline"] is True


def test_wf_test_010_bw04_s2_caretaker_reject(caretaker_client):
    """
    test_id: WF-TEST-010
    source_id: BW-VH-04 S2 caretaker-reject
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-010",
        indenter_id=201,
        is_offline=True,
        booking_source="telephonic",
        visit_purpose="Emergency Meeting",
        arrival_date=date.today() + timedelta(days=3),
        departure_date=date.today() + timedelta(days=5),
        status="pending_offline",
    )
    payload = {"action": "reject", "reason": "No rooms for offline booking"}
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/route/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"
    assert resp.data["rejection_reason"] == "No rooms for offline booking"


def test_wf_test_011_bw05_s1_offline_recorded(caretaker_client):
    """
    test_id: WF-TEST-011
    source_id: BW-VH-05 S1 offline-recorded
    """
    payload = {
        "booking_source": "walk_in",
        "visitor_name": "Walk In Guest",
        "visitor_category": "B",
        "visit_purpose": "Official Audit",
        "arrival_date": str(date.today() + timedelta(days=4)),
        "departure_date": str(date.today() + timedelta(days=6)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending_offline"


def test_wf_test_012_bw05_s2_caretaker_forward(caretaker_client):
    """
    test_id: WF-TEST-012
    source_id: BW-VH-05 S2 caretaker-forward
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-012",
        indenter_id=201,
        is_offline=True,
        booking_source="walk_in",
        visit_purpose="Official Audit",
        arrival_date=date.today() + timedelta(days=4),
        departure_date=date.today() + timedelta(days=6),
        status="pending_offline",
    )
    payload = {"action": "forward"}
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/route/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "forwarded_offline"


def test_wf_test_013_bw05_s3_incharge_approve(incharge_client):
    """
    test_id: WF-TEST-013
    source_id: BW-VH-05 S3 incharge-approve
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-013",
        indenter_id=201,
        is_offline=True,
        booking_source="walk_in",
        visit_purpose="Official Audit",
        arrival_date=date.today() + timedelta(days=4),
        departure_date=date.today() + timedelta(days=6),
        status="forwarded_offline",
    )
    payload = {"action": "approve"}
    resp = incharge_client.post(f"/api/v1/vh/bookings/{b.id}/decide/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved_offline"


def test_wf_test_014_bw06_s1_offline_recorded(caretaker_client):
    """
    test_id: WF-TEST-014
    source_id: BW-VH-06 S1 offline-recorded
    """
    payload = {
        "booking_source": "telephonic",
        "visitor_name": "Telephonic Delegate",
        "visitor_category": "C",
        "visit_purpose": "Conference Participant",
        "arrival_date": str(date.today() + timedelta(days=7)),
        "departure_date": str(date.today() + timedelta(days=9)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending_offline"


def test_wf_test_015_bw06_s2_caretaker_forward(caretaker_client):
    """
    test_id: WF-TEST-015
    source_id: BW-VH-06 S2 caretaker-forward
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-015",
        indenter_id=201,
        is_offline=True,
        booking_source="telephonic",
        visit_purpose="Conference Participant",
        arrival_date=date.today() + timedelta(days=7),
        departure_date=date.today() + timedelta(days=9),
        status="pending_offline",
    )
    payload = {"action": "forward"}
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/route/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "forwarded_offline"


def test_wf_test_016_bw06_s3_incharge_reject(incharge_client):
    """
    test_id: WF-TEST-016
    source_id: BW-VH-06 S3 incharge-reject
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-016",
        indenter_id=201,
        is_offline=True,
        booking_source="telephonic",
        visit_purpose="Conference Participant",
        arrival_date=date.today() + timedelta(days=7),
        departure_date=date.today() + timedelta(days=9),
        status="forwarded_offline",
    )
    payload = {"action": "reject", "reason": "Conference quota exceeded"}
    resp = incharge_client.post(f"/api/v1/vh/bookings/{b.id}/decide/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] in ["rejected", "rejected_offline"]
    assert resp.data["rejection_reason"] == "Conference quota exceeded"


def test_wf_test_017_bw07_s1_request_cancellation(indenter_client):
    """
    test_id: WF-TEST-017
    source_id: BW-VH-07 S1 request-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-017",
        indenter_id=101,
        visit_purpose="Future Visit",
        arrival_date=date.today() + timedelta(days=7),
        departure_date=date.today() + timedelta(days=9),
        status="approved",
    )
    payload = {"reason": "Cancelled well in advance"}
    resp = indenter_client.post(f"/api/v1/vh/bookings/{b.id}/cancel/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "cancellation_requested"
    assert Decimal(str(resp.data["cancellation_charge_percentage"])) == Decimal("0.00")


def test_wf_test_018_bw07_s2_confirm_cancellation(caretaker_client):
    """
    test_id: WF-TEST-018
    source_id: BW-VH-07 S2 confirm-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-018",
        indenter_id=101,
        visit_purpose="Future Visit",
        arrival_date=date.today() + timedelta(days=7),
        departure_date=date.today() + timedelta(days=9),
        status="cancellation_requested",
        cancellation_charge_percentage=Decimal("0.00"),
        cancellation_requested_at=timezone.now(),
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "cancelled"
    assert resp.data["cancellation_confirmed_at"] is not None


def test_wf_test_019_bw08_s1_request_cancellation(indenter_client):
    """
    test_id: WF-TEST-019
    source_id: BW-VH-08 S1 request-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-019",
        indenter_id=101,
        visit_purpose="Upcoming Visit",
        arrival_date=date.today() + timedelta(days=4),
        departure_date=date.today() + timedelta(days=6),
        status="approved",
    )
    payload = {"reason": "Short notice cancellation"}
    resp = indenter_client.post(f"/api/v1/vh/bookings/{b.id}/cancel/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "cancellation_requested"
    assert Decimal(str(resp.data["cancellation_charge_percentage"])) == Decimal("25.00")


def test_wf_test_020_bw08_s2_confirm_cancellation(caretaker_client):
    """
    test_id: WF-TEST-020
    source_id: BW-VH-08 S2 confirm-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-020",
        indenter_id=101,
        visit_purpose="Upcoming Visit",
        arrival_date=date.today() + timedelta(days=4),
        departure_date=date.today() + timedelta(days=6),
        status="cancellation_requested",
        cancellation_charge_percentage=Decimal("25.00"),
        cancellation_requested_at=timezone.now(),
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "cancelled"


def test_wf_test_021_bw09_s1_request_cancellation(indenter_client):
    """
    test_id: WF-TEST-021
    source_id: BW-VH-09 S1 request-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-021",
        indenter_id=101,
        visit_purpose="Today Visit",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="approved",
    )
    payload = {"reason": "Same day emergency"}
    resp = indenter_client.post(f"/api/v1/vh/bookings/{b.id}/cancel/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "cancellation_requested"
    assert Decimal(str(resp.data["cancellation_charge_percentage"])) == Decimal("50.00")


def test_wf_test_022_bw09_s2_confirm_cancellation(caretaker_client):
    """
    test_id: WF-TEST-022
    source_id: BW-VH-09 S2 confirm-cancellation
    """
    b = Booking.objects.create(
        booking_reference="BK-WF-022",
        indenter_id=101,
        visit_purpose="Today Visit",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="cancellation_requested",
        cancellation_charge_percentage=Decimal("50.00"),
        cancellation_requested_at=timezone.now(),
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "cancelled"


def test_wf_test_023_bw10_s1_allot_rooms(caretaker_client, sample_rooms):
    """
    test_id: WF-TEST-023
    source_id: BW-VH-10 S1 allot-rooms
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-WF-023",
        indenter_id=101,
        visit_purpose="Guest Stay",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="approved",
    )
    payload = {"room_ids": [r1.id], "occupancy_type": "single"}
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/allot-rooms/", payload, format="json"
    )
    assert resp.status_code == 200
    assert RoomAllotment.objects.filter(booking=b, room=r1).exists()
    b.refresh_from_db()
    assert b.status == "room_allotted"


def test_wf_test_024_bw10_s2_guest_checkin(caretaker_client, sample_rooms):
    """
    test_id: WF-TEST-024
    source_id: BW-VH-10 S2 guest-checkin
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-WF-024",
        indenter_id=101,
        visit_purpose="Guest Stay",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="room_allotted",
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/checkin/", format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "checked_in"
    assert resp.data["checkin_time"] is not None


def test_wf_test_025_bw10_s3_guest_checkout(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: WF-TEST-025
    source_id: BW-VH-10 S3 guest-checkout
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-WF-025",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Guest Stay",
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today(),
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=1),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")
    # Generate bill
    caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")

    # Checkout with verification
    payload = {"verified_by_guest": True}
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/checkout/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "checked_out"
    assert resp.data["checkout_time"] is not None


def test_wf_test_026_cw01_composite_booking_approval(
    indenter_client, caretaker_client, incharge_client, sample_rooms
):
    """
    test_id: WF-TEST-026
    source_id: CW-VH-01 composite-booking-approval
    """
    r1, _, _ = sample_rooms
    # 1. Indenter submits
    sub_payload = {
        "visitor_name": "Prof. Shannon",
        "visitor_category": "A",
        "visit_purpose": "Information Theory Keynote",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    s_resp = indenter_client.post("/api/v1/vh/bookings/", sub_payload, format="json")
    assert s_resp.status_code == 201
    bk_id = s_resp.data["id"]
    assert s_resp.data["status"] == "pending"

    # 2. Caretaker reviews and forwards
    f_resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{bk_id}/route/",
        {"action": "forward", "reason": "Verified guest profile"},
        format="json",
    )
    assert f_resp.status_code == 200
    assert f_resp.data["status"] == "forwarded"

    # 3. In-Charge approves
    a_resp = incharge_client.post(
        f"/api/v1/vh/bookings/{bk_id}/decide/",
        {"action": "approve", "reason": "Institute Guest approved"},
        format="json",
    )
    assert a_resp.status_code == 200
    assert a_resp.data["status"] == "approved"

    # 4. Caretaker allots room
    allot_resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{bk_id}/allot-rooms/",
        {"room_ids": [r1.id], "occupancy_type": "single"},
        format="json",
    )
    assert allot_resp.status_code == 200

    # 5. Checkin
    ci_resp = caretaker_client.post(f"/api/v1/vh/bookings/{bk_id}/checkin/", format="json")
    assert ci_resp.status_code == 200
    assert ci_resp.data["status"] == "checked_in"


def test_wf_test_027_cw02_composite_cancellation_billing(
    indenter_client, caretaker_client, sample_rooms, sample_tariffs
):
    """
    test_id: WF-TEST-027
    source_id: CW-VH-02 composite-cancellation-billing
    """
    r1, _, _ = sample_rooms
    # 1. Approved booking with suite allotted
    b = Booking.objects.create(
        booking_reference="BK-CW-027",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Cancelled trip",
        arrival_date=date.today() + timedelta(days=3),
        departure_date=date.today() + timedelta(days=5),
        status="approved",
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")

    # 2. Cancellation requested 3 days before arrival -> 25% charge
    c_resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Flight cancelled"},
        format="json",
    )
    assert c_resp.status_code == 200
    assert c_resp.data["status"] == "cancellation_requested"
    assert Decimal(str(c_resp.data["cancellation_charge_percentage"])) == Decimal("25.00")

    # 3. Caretaker confirms cancellation
    conf_resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json"
    )
    assert conf_resp.status_code == 200
    assert conf_resp.data["status"] == "cancelled"

    # 4. Generate bill (25% of 800.00 = 200.00)
    bill_resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert bill_resp.status_code == 201
    assert Decimal(str(bill_resp.data["cancellation_charge_total"])) == Decimal("200.00")
    bill_id = bill_resp.data["id"]

    # 5. Settle bill offline cash
    set_resp = caretaker_client.post(
        f"/api/v1/vh/bills/{bill_id}/settle/",
        {
            "payment_mode": "offline_cash",
            "amount_paid": "200.00",
            "receipt_number": "REC-CW-027",
        },
        format="json",
    )
    assert set_resp.status_code == 200
    assert set_resp.data["payment_mode"] == "offline_cash"

    bill = Bill.objects.get(id=bill_id)
    assert bill.status == "settled"
    assert bill.is_immutable is True
