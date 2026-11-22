# End-to-end HTTP journey tests for VHMS basis and composite workflows and use cases.
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.roles import OperationalRoleHolder

pytestmark = pytest.mark.django_db


def test_uc_vh_001_and_bw_vh_01_direct_rejection(indenter_client, caretaker_client):
    # UC-VH-001, UC-VH-003, BW-VH-01: Indenter submits online booking -> Caretaker rejects directly
    payload = {
        "visitor_name": "Dr. Alan Turing",
        "visitor_email": "turing@cam.ac.uk",
        "visitor_category": "A",
        "visit_purpose": "Guest Lecture on Computation",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    booking_id = resp.data["id"]
    assert resp.data["status"] == "pending"

    # Caretaker rejects directly
    resp_reject = caretaker_client.post(
        f"/api/v1/vh/bookings/{booking_id}/route/",
        {"action": "reject", "reason": "No capacity for institute guests"},
        format="json",
    )
    assert resp_reject.status_code == 200
    assert resp_reject.data["status"] == "rejected"
    assert resp_reject.data["rejection_reason"] == "No capacity for institute guests"


def test_uc_vh_001_and_bw_vh_02_forwarded_and_approved(
    indenter_client, caretaker_client, incharge_client
):
    # UC-VH-001, UC-VH-003, UC-VH-004, BW-VH-02: Online booking -> Caretaker forwards -> Incharge approves
    payload = {
        "visitor_name": "Prof. Ada Lovelace",
        "visitor_category": "B",
        "visit_purpose": "Keynote at CS Conference",
        "arrival_date": str(date.today() + timedelta(days=14)),
        "departure_date": str(date.today() + timedelta(days=16)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "project",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code == 201
    b_id = resp.data["id"]

    # Caretaker forwards
    resp_fwd = caretaker_client.post(
        f"/api/v1/vh/bookings/{b_id}/route/", {"action": "forward"}, format="json"
    )
    assert resp_fwd.status_code == 200
    assert resp_fwd.data["status"] == "forwarded"

    # Incharge approves
    resp_app = incharge_client.post(
        f"/api/v1/vh/bookings/{b_id}/decide/", {"action": "approve"}, format="json"
    )
    assert resp_app.status_code == 200
    assert resp_app.data["status"] == "approved"


def test_uc_vh_001_and_bw_vh_03_forwarded_and_rejected(
    indenter_client, caretaker_client, incharge_client
):
    # UC-VH-001, UC-VH-003, UC-VH-004, BW-VH-03: Online booking -> Caretaker forwards -> Incharge rejects
    payload = {
        "visitor_name": "Prof. Claude Shannon",
        "visitor_category": "A",
        "visit_purpose": "Information Theory Seminar",
        "arrival_date": str(date.today() + timedelta(days=20)),
        "departure_date": str(date.today() + timedelta(days=22)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    b_id = resp.data["id"]

    caretaker_client.post(
        f"/api/v1/vh/bookings/{b_id}/route/", {"action": "forward"}, format="json"
    )
    resp_rej = incharge_client.post(
        f"/api/v1/vh/bookings/{b_id}/decide/",
        {"action": "reject", "reason": "Hostel reserved for Institute Foundation Day"},
        format="json",
    )
    assert resp_rej.status_code == 200
    assert resp_rej.data["status"] == "rejected"


def test_uc_vh_005_and_bw_vh_04_to_06_offline_bookings(caretaker_client, incharge_client):
    # UC-VH-005, BW-VH-04..06: Offline bookings flagged correctly and subjected to same routing
    payload = {
        "booking_source": "walk_in",
        "visitor_name": "Walk-in Guest John",
        "visitor_category": "C",
        "visit_purpose": "Urgent technical consultation",
        "arrival_date": str(date.today() + timedelta(days=3)),
        "departure_date": str(date.today() + timedelta(days=5)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    b_id = resp.data["id"]
    assert resp.data["is_offline"] is True
    assert resp.data["status"] == "pending_offline"

    # Forward and approve
    caretaker_client.post(
        f"/api/v1/vh/bookings/{b_id}/route/", {"action": "forward"}, format="json"
    )
    resp_app = incharge_client.post(
        f"/api/v1/vh/bookings/{b_id}/decide/", {"action": "approve"}, format="json"
    )
    assert resp_app.status_code == 200
    assert resp_app.data["status"] == "approved_offline"


def test_uc_vh_007_and_bw_vh_07_cancellation_7_days(indenter_client, caretaker_client):
    # BW-VH-07, BR-VH-007: Exactly 7 days before arrival = 0% cancellation charge
    arr = date.today() + timedelta(days=7)
    b = Booking.objects.create(
        booking_reference="VH-CANCEL-7D",
        indenter_id=101,
        arrival_date=arr,
        departure_date=arr + timedelta(days=2),
        status="pending",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/", {"reason": "Plans changed"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "cancellation_requested"
    assert Decimal(resp.data["cancellation_charge_percentage"]) == Decimal("0.00")

    # Caretaker confirms
    resp_conf = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json"
    )
    assert resp_conf.status_code == 200
    assert resp_conf.data["status"] == "cancelled"


def test_uc_vh_007_and_bw_vh_08_cancellation_within_7_days(
    indenter_client, caretaker_client, sample_tariffs
):
    # BW-VH-08, BR-VH-008: 3 days before arrival = 25% cancellation charge
    arr = date.today() + timedelta(days=3)
    b = Booking.objects.create(
        booking_reference="VH-CANCEL-3D",
        indenter_id=101,
        visitor_category="A",
        arrival_date=arr,
        departure_date=arr + timedelta(days=2),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/", {"reason": "Emergency"}, format="json"
    )
    assert resp.status_code == 200
    assert Decimal(resp.data["cancellation_charge_percentage"]) == Decimal("25.00")

    caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json")
    bill = Bill.objects.get(booking=b)
    assert bill.cancellation_charge_total > Decimal("0.00")


def test_uc_vh_007_and_bw_vh_09_cancellation_same_day(
    indenter_client, caretaker_client, sample_tariffs
):
    # BW-VH-09, BR-VH-009: Same day cancellation = 50% cancellation charge
    arr = date.today()
    b = Booking.objects.create(
        booking_reference="VH-CANCEL-0D",
        indenter_id=101,
        visitor_category="A",
        arrival_date=arr,
        departure_date=arr + timedelta(days=2),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/", {"reason": "Flight cancelled"}, format="json"
    )
    assert resp.status_code == 200
    assert Decimal(resp.data["cancellation_charge_percentage"]) == Decimal("50.00")

    caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/confirm-cancellation/", format="json")
    bill = Bill.objects.get(booking=b)
    assert bill.cancellation_charge_total > Decimal("0.00")


def test_bw_vh_10_full_stay_journey(caretaker_client, sample_rooms, sample_tariffs):
    # BW-VH-10: Approved -> Room Allotted -> Checked In -> Checked Out & Billed & Settled
    r1, _, _ = sample_rooms
    today = date.today()
    booking = Booking.objects.create(
        booking_reference="VH-STAY-FULL",
        indenter_id=101,
        visitor_category="A",
        arrival_date=today,
        departure_date=today + timedelta(days=2),
        status="approved",
    )

    # 1. Allot Room (UC-VH-008)
    resp_allot = caretaker_client.post(
        f"/api/v1/vh/bookings/{booking.id}/allot-rooms/",
        {"room_ids": [r1.id], "occupancy_type": "single"},
        format="json",
    )
    assert resp_allot.status_code == 200
    booking.refresh_from_db()
    assert booking.status == "room_allotted"

    # 2. Check-in (UC-VH-009)
    resp_in = caretaker_client.post(f"/api/v1/vh/bookings/{booking.id}/checkin/", format="json")
    assert resp_in.status_code == 200
    booking.refresh_from_db()
    assert booking.status == "checked_in"

    # 3. Order Meals (UC-VH-012)
    resp_meal = caretaker_client.post(
        f"/api/v1/vh/bookings/{booking.id}/meals/",
        {"meal_date": str(today), "meal_option": "full_day", "quantity": 1},
        format="json",
    )
    assert resp_meal.status_code == 201

    # 4. Check-out and verify bill (UC-VH-021)
    resp_out = caretaker_client.post(
        f"/api/v1/vh/bookings/{booking.id}/checkout/",
        {"verified_by_guest": True},
        format="json",
    )
    assert resp_out.status_code == 200
    booking.refresh_from_db()
    assert booking.status == "checked_out"

    # 5. Verify Bill and Offline Cash Settlement (UC-VH-013)
    bill = Bill.objects.get(booking=booking)
    assert bill.room_rent_total > Decimal("0.00")
    assert bill.meal_charge_total > Decimal("0.00")
    assert bill.status == "verified"

    resp_settle = caretaker_client.post(
        f"/api/v1/vh/bills/{bill.id}/settle/",
        {
            "amount_paid": str(bill.total_amount),
            "receipt_number": "RCP-FULL-1",
            "notes": "Cash settlement",
        },
        format="json",
    )
    assert resp_settle.status_code == 200
    bill.refresh_from_db()
    assert bill.status == "settled"
    assert bill.is_immutable is True


def test_inventory_replenishment_journey(caretaker_client, incharge_client, sample_inventory):
    # UC-VH-014, UC-VH-015: Caretaker requests replenishment -> VH In-Charge approves
    item1, _ = sample_inventory
    initial_qty = item1.current_quantity

    resp_req = caretaker_client.post(
        f"/api/v1/vh/inventory/{item1.id}/replenish/",
        {"requested_quantity": 10, "remarks": "Restocking linen for upcoming peak season"},
        format="json",
    )
    assert resp_req.status_code == 201
    rep_id = resp_req.data["id"]

    resp_app = incharge_client.post(
        f"/api/v1/vh/inventory/replenishments/{rep_id}/approve/",
        {"decision": "approved", "remarks": "Approved as per budget"},
        format="json",
    )
    assert resp_app.status_code == 200
    assert resp_app.data["status"] == "approved"
    item1.refresh_from_db()
    assert item1.current_quantity == initial_qty + 10


def test_role_reassignment_journey(incharge_client):
    # UC-VH-019, BR-VH-045..050: Role reassignment immediately takes effect and transfers records
    resp = incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {"role_name": "caretaker", "new_user_id": 999},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["user_id"] == 999
    assert OperationalRoleHolder.objects.filter(role_name="caretaker", is_active=True).count() == 1


def test_reports_views_journey(caretaker_client, incharge_client, db):
    # UC-VH-017, UC-VH-018: Caretaker and In-Charge reports viewable
    resp_ct = caretaker_client.get("/api/v1/vh/reports/caretaker/?report_type=occupancy")
    assert resp_ct.status_code == 200
    assert "total_rooms_occupied" in resp_ct.data

    resp_ic = incharge_client.get("/api/v1/vh/reports/incharge/?report_type=summary")
    assert resp_ic.status_code == 200
    assert "total_bookings" in resp_ic.data
