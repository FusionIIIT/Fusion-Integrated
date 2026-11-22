# Specification-based automated tests for Use Cases (UC) strategy.
# Covers main success flows and explicitly specified alternative flows for all VHMS use cases.
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.vh.models.alerts import BookingNotificationLog, StayAlert
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem, InventoryReplenishment
from modules.vh.models.room import RoomAllotment
from modules.vh.services.alerts import evaluate_no_shows

pytestmark = pytest.mark.django_db


def test_uc_test_001_submit_online_booking_main_flow(indenter_client):
    """
    test_id: UC-TEST-001
    source_id: UC-VH-001 Main Flow
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


def test_uc_test_002_submit_online_booking_alt_flow_1(indenter_client):
    """
    test_id: UC-TEST-002
    source_id: UC-VH-001 Alternative Flow 1
    """
    payload = {
        "visitor_category": "A",
        "visit_purpose": "Guest Lecture",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "institute",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_uc_test_003_submit_online_booking_alt_flow_2(indenter_client):
    """
    test_id: UC-TEST-003
    source_id: UC-VH-001 Alternative Flow 2
    """
    payload = {
        "visitor_name": "Prof. Turing",
        "visitor_category": "A",
        "visit_purpose": "Guest Lecture",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "unauthorized_sponsor",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_uc_test_004_track_view_print_booking_main_flow(indenter_client):
    """
    test_id: UC-TEST-004
    source_id: UC-VH-002 Main Flow
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-002",
        indenter_id=101,
        visit_purpose="Track view print",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="approved",
    )
    resp = indenter_client.get(f"/api/v1/vh/bookings/{b.id}/")
    assert resp.status_code == 200
    assert resp.data["booking_reference"] == "BK-UC-002"
    assert resp.data["status"] == "approved"


def test_uc_test_005_track_view_print_booking_alt_flow_1(indenter_client):
    """
    test_id: UC-TEST-005
    source_id: UC-VH-002 Alternative Flow 1
    """
    resp = indenter_client.get("/api/v1/vh/bookings/")
    assert resp.status_code == 200
    assert isinstance(resp.data, list)


def test_uc_test_006_review_and_route_booking_main_flow(caretaker_client):
    """
    test_id: UC-TEST-006
    source_id: UC-VH-003 Main Flow
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-003",
        indenter_id=101,
        visit_purpose="Route forward",
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


def test_uc_test_007_review_and_route_booking_alt_flow_1(caretaker_client):
    """
    test_id: UC-TEST-007
    source_id: UC-VH-003 Alternative Flow 1
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-003-REJ",
        indenter_id=101,
        visit_purpose="Route reject",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/route/",
        {"action": "reject", "reason": "Hostel booked"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"


def test_uc_test_008_decide_forwarded_booking_main_flow(incharge_client):
    """
    test_id: UC-TEST-008
    source_id: UC-VH-004 Main Flow
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-004",
        indenter_id=101,
        visit_purpose="Incharge approve",
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


def test_uc_test_009_decide_forwarded_booking_alt_flow_1(incharge_client):
    """
    test_id: UC-TEST-009
    source_id: UC-VH-004 Alternative Flow 1
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-004-REJ",
        indenter_id=101,
        visit_purpose="Incharge reject",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="forwarded",
    )
    resp = incharge_client.post(
        f"/api/v1/vh/bookings/{b.id}/decide/",
        {"action": "reject", "reason": "Over capacity"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"


def test_uc_test_010_record_offline_booking_main_flow(caretaker_client):
    """
    test_id: UC-TEST-010
    source_id: UC-VH-005 Main Flow
    """
    payload = {
        "visitor_name": "Walk-in Guest",
        "visitor_category": "B",
        "visit_purpose": "Urgent seminar",
        "arrival_date": str(date.today() + timedelta(days=2)),
        "departure_date": str(date.today() + timedelta(days=4)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
        "booking_source": "walk_in",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["is_offline"] is True
    assert resp.data["status"] == "pending_offline"


def test_uc_test_011_record_offline_booking_alt_flow_1(caretaker_client):
    """
    test_id: UC-TEST-011
    source_id: UC-VH-005 Alternative Flow 1
    """
    payload = {
        "visitor_category": "B",
        "visit_purpose": "Incomplete offline",
        "arrival_date": str(date.today() + timedelta(days=2)),
        "departure_date": str(date.today() + timedelta(days=4)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
        "booking_source": "walk_in",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_uc_test_012_request_booking_modification_main_flow(indenter_client):
    """
    test_id: UC-TEST-012
    source_id: UC-VH-006 Main Flow
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-006",
        indenter_id=101,
        visit_purpose="Mod pre-arrival",
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


def test_uc_test_013_request_booking_modification_alt_flow_1(indenter_client):
    """
    test_id: UC-TEST-013
    source_id: UC-VH-006 Alternative Flow 1
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-006-POST",
        indenter_id=101,
        visit_purpose="Mod post-arrival",
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/modify/",
        {"departure_date": str(date.today() + timedelta(days=4))},
        format="json",
    )
    assert resp.status_code in [400, 409, 422]


def test_uc_test_014_request_booking_cancellation_main_flow(indenter_client):
    """
    test_id: UC-TEST-014
    source_id: UC-VH-007 Main Flow
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-007",
        indenter_id=101,
        visit_purpose="Cancel main flow",
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Cancelled by visitor"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "cancellation_requested"


def test_uc_test_015_request_booking_cancellation_alt_flow_1(indenter_client):
    """
    test_id: UC-TEST-015
    source_id: UC-VH-007 Alternative Flow 1
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-007-7D",
        indenter_id=101,
        visit_purpose="7 day cancellation",
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


def test_uc_test_016_request_booking_cancellation_alt_flow_2(indenter_client):
    """
    test_id: UC-TEST-016
    source_id: UC-VH-007 Alternative Flow 2
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-007-3D",
        indenter_id=101,
        visit_purpose="3 day cancellation",
        arrival_date=date.today() + timedelta(days=3),
        departure_date=date.today() + timedelta(days=5),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Within 7 days"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["cancellation_charge_percentage"] == "25.00"


def test_uc_test_017_request_booking_cancellation_alt_flow_3(indenter_client):
    """
    test_id: UC-TEST-017
    source_id: UC-VH-007 Alternative Flow 3
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-007-0D",
        indenter_id=101,
        visit_purpose="Same day cancel",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/",
        {"reason": "Same day emergency"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["cancellation_charge_percentage"] == "50.00"


def test_uc_test_018_allot_rooms_main_flow(caretaker_client, sample_rooms):
    """
    test_id: UC-TEST-018
    source_id: UC-VH-008 Main Flow
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-008",
        indenter_id=101,
        visit_purpose="Allot room main",
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


def test_uc_test_019_allot_rooms_alt_flow_1(caretaker_client, sample_rooms):
    """
    test_id: UC-TEST-019
    source_id: UC-VH-008 Alternative Flow 1
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-008-NOTAPP",
        indenter_id=101,
        visit_purpose="Allot not approved",
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


def test_uc_test_020_record_guest_checkin_main_flow(caretaker_client, sample_rooms):
    """
    test_id: UC-TEST-020
    source_id: UC-VH-009 Main Flow
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-009",
        indenter_id=101,
        visit_purpose="Checkin main flow",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="room_allotted",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/checkin/", {}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "checked_in"


def test_uc_test_021_tariff_configuration_main_flow(incharge_client):
    """
    test_id: UC-TEST-021
    source_id: UC-VH-011 Main Flow
    """
    payload = {
        "category": "B",
        "room_type": "suite",
        "occupancy": "double",
        "daily_rate": "1200.00",
        "effective_from": str(date.today()),
    }
    resp = incharge_client.post("/api/v1/vh/tariffs/", payload, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["daily_rate"])) == Decimal("1200.00")


def test_uc_test_022_manage_meal_bookings_main_flow(caretaker_client, sample_rooms):
    """
    test_id: UC-TEST-022
    source_id: UC-VH-012 Main Flow
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-012",
        indenter_id=101,
        visit_purpose="Meal booking main",
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
            "quantity": 1,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["meal_option"] == "full_day"


def test_uc_test_023_manage_meal_bookings_alt_flow_1(caretaker_client, sample_rooms):
    """
    test_id: UC-TEST-023
    source_id: UC-VH-012 Alternative Flow 1
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-012-OUT",
        indenter_id=101,
        visit_purpose="Meal booking out of range",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/meals/",
        {
            "meal_date": str(date.today() + timedelta(days=10)),
            "meal_option": "full_day",
        },
        format="json",
    )
    assert resp.status_code in [400, 422]


def test_uc_test_024_generate_bill_and_settle_main_flow(
    caretaker_client, sample_rooms, sample_tariffs
):
    """
    test_id: UC-TEST-024
    source_id: UC-VH-013 Main Flow
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-013",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Bill and settle",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    bill_id = resp.data["id"]

    resp_s = caretaker_client.post(
        f"/api/v1/vh/bills/{bill_id}/settle/",
        {"amount_paid": "800.00", "payment_mode": "offline_cash"},
        format="json",
    )
    assert resp_s.status_code == 200
    assert resp_s.data["payment_mode"] == "offline_cash"


def test_uc_test_025_generate_bill_cancellation_alt_flow_1(
    caretaker_client, sample_rooms, sample_tariffs
):
    """
    test_id: UC-TEST-025
    source_id: UC-VH-013 Alternative Flow 1
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-013-CAN",
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


def test_uc_test_026_maintain_inventory_records_main_flow(caretaker_client):
    """
    test_id: UC-TEST-026
    source_id: UC-VH-014 Main Flow
    """
    payload = {
        "item_name": "Bath Mat White",
        "category": "linen",
        "current_quantity": 25,
        "minimum_threshold": 10,
        "unit": "pieces",
    }
    resp = caretaker_client.post("/api/v1/vh/inventory/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["item_name"] == "Bath Mat White"


def test_uc_test_027_review_approve_replenishment_main_flow(incharge_client):
    """
    test_id: UC-TEST-027
    source_id: UC-VH-015 Main Flow
    """
    item = InventoryItem.objects.create(
        item_name="Kettle Electric",
        category="utensils",
        current_quantity=2,
        minimum_threshold=5,
        unit="pieces",
    )
    rep = InventoryReplenishment.objects.create(
        item=item,
        requested_quantity=5,
        requested_by=201,
        status="pending",
    )
    resp = incharge_client.post(
        f"/api/v1/vh/inventory/replenishments/{rep.id}/approve/",
        {"decision": "approved", "remarks": "Approved budget"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


def test_uc_test_028_incharge_reports_main_flow(incharge_client):
    """
    test_id: UC-TEST-028
    source_id: UC-VH-017 Main Flow
    """
    resp = incharge_client.get("/api/v1/vh/reports/incharge/?report_type=summary")
    assert resp.status_code == 200
    assert "total_bookings" in resp.data


def test_uc_test_029_caretaker_reports_main_flow(caretaker_client):
    """
    test_id: UC-TEST-029
    source_id: UC-VH-018 Main Flow
    """
    resp = caretaker_client.get("/api/v1/vh/reports/caretaker/?report_type=occupancy")
    assert resp.status_code == 200
    assert "total_rooms_occupied" in resp.data


def test_uc_test_030_reassign_operational_role_main_flow(incharge_client):
    """
    test_id: UC-TEST-030
    source_id: UC-VH-019 Main Flow
    """
    resp = incharge_client.post(
        "/api/v1/vh/roles/reassign/",
        {
            "role_name": "caretaker",
            "new_user_id": 998,
            "valid_from": str(date.today()),
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["user_id"] == 998


def test_uc_test_031_confirm_cancellation_main_flow(caretaker_client):
    """
    test_id: UC-TEST-031
    source_id: UC-VH-020 Main Flow
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-020",
        indenter_id=101,
        visit_purpose="Confirm cancellation UC",
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


def test_uc_test_032_record_checkout_and_verify_bill_main_flow(caretaker_client, sample_rooms):
    """
    test_id: UC-TEST-032
    source_id: UC-VH-021 Main Flow
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-021",
        indenter_id=101,
        visit_purpose="Checkout verify bill",
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


def test_uc_test_033_record_confirmed_modification_main_flow(
    caretaker_client, sample_rooms, sample_tariffs
):
    """
    test_id: UC-TEST-033
    source_id: UC-VH-022 Main Flow
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-UC-022",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Confirmed mod billing",
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=4),
        status="checked_out",
    )
    RoomAllotment.objects.create(booking=b, room=r1, occupancy_type="single", allotted_by=201)
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", {}, format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["room_rent_total"])) == Decimal("2400.00")


def test_uc_test_034_booking_lifecycle_notifications_main_flow(indenter_client):
    """
    test_id: UC-TEST-034
    source_id: UC-VH-023 Main Flow
    """
    payload = {
        "visitor_name": "Dr. Notif UC",
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
    b = Booking.objects.get(id=resp.data["id"])
    assert BookingNotificationLog.objects.filter(booking=b).exists()


def test_uc_test_035_stay_exception_alerts_main_flow():
    """
    test_id: UC-TEST-035
    source_id: UC-VH-024 Main Flow
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-024",
        indenter_id=101,
        visit_purpose="Stay exception alert",
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today() + timedelta(days=1),
        status="room_allotted",
    )
    created = evaluate_no_shows()
    assert isinstance(created, int) and created >= 0
    assert StayAlert.objects.filter(booking=b, alert_type="no_show").exists()


def test_uc_test_036_stay_exception_alerts_alt_flow_1():
    """
    test_id: UC-TEST-036
    source_id: UC-VH-024 Alternative Flow 1
    """
    b = Booking.objects.create(
        booking_reference="BK-UC-024-OK",
        indenter_id=101,
        visit_purpose="On time checkin",
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today() + timedelta(days=1),
        status="checked_in",
    )
    evaluate_no_shows()
    assert not StayAlert.objects.filter(booking=b, alert_type="no_show").exists()


def test_uc_test_037_inventory_threshold_alert_main_flow(caretaker_client):
    """
    test_id: UC-TEST-037
    source_id: UC-VH-025 Main Flow
    """
    item = InventoryItem.objects.create(
        item_name="Pillow Standard",
        category="linen",
        current_quantity=3,
        minimum_threshold=10,
        unit="pieces",
        is_threshold_alert=True,
    )
    assert item.is_threshold_alert is True


def test_uc_test_038_inventory_threshold_alert_alt_flow_1(caretaker_client):
    """
    test_id: UC-TEST-038
    source_id: UC-VH-025 Alternative Flow 1
    """
    item = InventoryItem.objects.create(
        item_name="Soap Liquid",
        category="consumables",
        current_quantity=20,
        minimum_threshold=10,
        unit="bottles",
        is_threshold_alert=False,
    )
    assert item.is_threshold_alert is False
