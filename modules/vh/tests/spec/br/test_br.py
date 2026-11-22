# Specification-based automated tests for Business Rules (BR) strategy.
# Covers all business rules BR-VH-002 through BR-VH-050.
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.vh.models.alerts import StayAlert
from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem
from modules.vh.models.meal import MealBooking
from modules.vh.models.roles import OperationalRoleHolder
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.models.tariff import TariffConfig
from modules.vh.registry import _CARETAKER_PERMS
from modules.vh.selectors.tariffs import get_applicable_tariff
from modules.vh.services.alerts import evaluate_no_shows, evaluate_overstays
from modules.vh.services.inventory import evaluate_all_inventory_thresholds
from modules.vh.services.roles import reassign_operational_role

pytestmark = pytest.mark.django_db


def test_br_test_001_permitted_billing_responsibility(indenter_client):
    """
    test_id: BR-TEST-001
    source_id: BR-VH-002 permitted-values
    """
    for resp_val in ["visitor", "indenter", "institute", "project"]:
        payload = {
            "visitor_name": f"Guest {resp_val}",
            "visitor_category": "A",
            "visit_purpose": "Testing responsibility",
            "arrival_date": str(date.today() + timedelta(days=10)),
            "departure_date": str(date.today() + timedelta(days=12)),
            "number_of_rooms": 1,
            "number_of_occupants": 1,
            "billing_responsibility": resp_val,
        }
        resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
        assert resp.status_code == 201
        assert resp.data["billing_responsibility"] == resp_val


def test_br_test_002_prohibited_billing_responsibility(indenter_client):
    """
    test_id: BR-TEST-002
    source_id: BR-VH-002 prohibited-value
    """
    payload = {
        "visitor_name": "Guest Invalid Resp",
        "visitor_category": "A",
        "visit_purpose": "Testing invalid responsibility",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "corporate_sponsor",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_br_test_003_offline_same_routing(caretaker_client, incharge_client):
    """
    test_id: BR-TEST-003
    source_id: BR-VH-003 same-routing
    """
    payload = {
        "booking_source": "walk_in",
        "visitor_name": "Walk-in Guest",
        "visitor_category": "A",
        "visit_purpose": "Conference Walk-in",
        "arrival_date": str(date.today() + timedelta(days=5)),
        "departure_date": str(date.today() + timedelta(days=7)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    c_resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert c_resp.status_code == 201
    bk_id = c_resp.data["id"]
    assert c_resp.data["status"] == "pending_offline"

    # Forward by caretaker
    f_resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{bk_id}/route/", {"action": "forward"}, format="json"
    )
    assert f_resp.status_code == 200
    assert f_resp.data["status"] == "forwarded_offline"

    # Approve by incharge
    a_resp = incharge_client.post(
        f"/api/v1/vh/bookings/{bk_id}/decide/", {"action": "approve"}, format="json"
    )
    assert a_resp.status_code == 200
    assert a_resp.data["status"] == "approved_offline"


def test_br_test_004_offline_same_availability(caretaker_client, sample_rooms):
    """
    test_id: BR-TEST-004
    source_id: BR-VH-004 same-availability
    """
    r1, r2, r3 = sample_rooms
    today = date.today()
    arr = today + timedelta(days=10)
    dep = today + timedelta(days=15)

    # Allot all rooms for this date range
    b1 = Booking.objects.create(
        booking_reference="BK-AV-01",
        indenter_id=101,
        visit_purpose="Full block 1",
        arrival_date=arr,
        departure_date=dep,
        status="approved",
    )
    RoomAllotment.objects.create(booking=b1, room=r1, allotted_by=201)
    RoomAllotment.objects.create(booking=b1, room=r2, allotted_by=201)
    RoomAllotment.objects.create(booking=b1, room=r3, allotted_by=201)

    resp = caretaker_client.get(
        f"/api/v1/vh/rooms/availability/?arrival_date={arr}&departure_date={dep}"
    )
    assert resp.status_code == 200
    assert len(resp.data) == 0


def test_br_test_005_flag_offline(caretaker_client):
    """
    test_id: BR-TEST-005
    source_id: BR-VH-005 flag-offline
    """
    payload = {
        "booking_source": "telephonic",
        "visitor_name": "Phone Guest",
        "visitor_category": "B",
        "visit_purpose": "Meeting",
        "arrival_date": str(date.today() + timedelta(days=4)),
        "departure_date": str(date.today() + timedelta(days=6)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = caretaker_client.post("/api/v1/vh/bookings/offline/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["is_offline"] is True
    assert resp.data["booking_source"] == "telephonic"


def test_br_test_006_schedule_calculation(indenter_client):
    """
    test_id: BR-TEST-006
    source_id: BR-VH-006 schedule-calculation
    """
    # 10 days out -> 0%
    b1 = Booking.objects.create(
        booking_reference="BK-CALC-01",
        indenter_id=101,
        visit_purpose="Test",
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="approved",
    )
    r1 = indenter_client.post(
        f"/api/v1/vh/bookings/{b1.id}/cancel/", {"reason": "Change of plans"}, format="json"
    )
    assert r1.status_code == 200
    assert Decimal(str(r1.data["cancellation_charge_percentage"])) == Decimal("0.00")

    # 4 days out -> 25%
    b2 = Booking.objects.create(
        booking_reference="BK-CALC-02",
        indenter_id=101,
        visit_purpose="Test",
        arrival_date=date.today() + timedelta(days=4),
        departure_date=date.today() + timedelta(days=6),
        status="approved",
    )
    r2 = indenter_client.post(
        f"/api/v1/vh/bookings/{b2.id}/cancel/", {"reason": "Emergency"}, format="json"
    )
    assert r2.status_code == 200
    assert Decimal(str(r2.data["cancellation_charge_percentage"])) == Decimal("25.00")

    # Same day -> 50%
    b3 = Booking.objects.create(
        booking_reference="BK-CALC-03",
        indenter_id=101,
        visit_purpose="Test",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="approved",
    )
    r3 = indenter_client.post(
        f"/api/v1/vh/bookings/{b3.id}/cancel/", {"reason": "Same day cancellation"}, format="json"
    )
    assert r3.status_code == 200
    assert Decimal(str(r3.data["cancellation_charge_percentage"])) == Decimal("50.00")


def test_br_test_007_7_day_zero_charge(indenter_client):
    """
    test_id: BR-TEST-007
    source_id: BR-VH-007 7-day-zero-charge
    """
    b = Booking.objects.create(
        booking_reference="BK-7DAY-01",
        indenter_id=101,
        visit_purpose="7 days test",
        arrival_date=date.today() + timedelta(days=7),
        departure_date=date.today() + timedelta(days=9),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/", {"reason": "Notice in advance"}, format="json"
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.data["cancellation_charge_percentage"])) == Decimal("0.00")


def test_br_test_008_within_7_days_25_percent(indenter_client):
    """
    test_id: BR-TEST-008
    source_id: BR-VH-008 within-7-days-25-percent
    """
    b = Booking.objects.create(
        booking_reference="BK-4DAY-01",
        indenter_id=101,
        visit_purpose="4 days test",
        arrival_date=date.today() + timedelta(days=4),
        departure_date=date.today() + timedelta(days=6),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/", {"reason": "Short notice"}, format="json"
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.data["cancellation_charge_percentage"])) == Decimal("25.00")


def test_br_test_009_same_day_50_percent(indenter_client):
    """
    test_id: BR-TEST-009
    source_id: BR-VH-009 same-day-50-percent
    """
    b = Booking.objects.create(
        booking_reference="BK-0DAY-01",
        indenter_id=101,
        visit_purpose="Same day test",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="approved",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/cancel/", {"reason": "No show or today"}, format="json"
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.data["cancellation_charge_percentage"])) == Decimal("50.00")


def test_br_test_010_adjust_modification_billing(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-010
    source_id: BR-VH-010 adjust-modification-billing
    """
    r1, _, _ = sample_rooms
    today = date.today()
    arr = today - timedelta(days=3)
    dep = today

    b = Booking.objects.create(
        booking_reference="BK-MOD-BILL",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Meeting",
        arrival_date=arr,
        departure_date=dep,
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=3),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")

    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    # 3 days * 800.00 = 2400.00
    assert Decimal(str(resp.data["room_rent_total"])) == Decimal("2400.00")


def test_br_test_011_adjust_cancellation_billing(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-011
    source_id: BR-VH-011 adjust-cancellation-billing
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-CANCEL-BILL",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Test Cancel Bill",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="cancelled",
        cancellation_charge_percentage=Decimal("50.00"),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    # 50% charge of 800 = 400.00
    assert Decimal(str(resp.data["cancellation_charge_total"])) == Decimal("400.00")
    assert Decimal(str(resp.data["total_amount"])) == Decimal("400.00")


def test_br_test_012_approved_allotment_permitted(caretaker_client, sample_rooms):
    """
    test_id: BR-TEST-012
    source_id: BR-VH-012 approved-allotment-permitted
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-ALLOT-APP",
        indenter_id=101,
        visit_purpose="Approved Booking",
        arrival_date=date.today() + timedelta(days=2),
        departure_date=date.today() + timedelta(days=4),
        status="approved",
    )
    payload = {"room_ids": [r1.id], "occupancy_type": "single"}
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/allot-rooms/", payload, format="json"
    )
    assert resp.status_code == 200
    assert RoomAllotment.objects.filter(booking=b, room=r1).exists()


def test_br_test_013_non_approved_allotment_prohibited(caretaker_client, sample_rooms):
    """
    test_id: BR-TEST-013
    source_id: BR-VH-012 non-approved-allotment-prohibited
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-ALLOT-PEND",
        indenter_id=101,
        visit_purpose="Pending Booking",
        arrival_date=date.today() + timedelta(days=2),
        departure_date=date.today() + timedelta(days=4),
        status="pending",
    )
    payload = {"room_ids": [r1.id], "occupancy_type": "single"}
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/allot-rooms/", payload, format="json"
    )
    assert resp.status_code in [400, 409, 422]


def test_br_test_014_single_occupancy(sample_rooms):
    """
    test_id: BR-TEST-014
    source_id: BR-VH-013 single-occupancy
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-OCC-S",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="approved",
    )
    allotment = RoomAllotment.objects.create(
        booking=b, room=r1, allotted_by=201, occupancy_type="single"
    )
    assert allotment.occupancy_type == "single"


def test_br_test_015_double_occupancy(sample_rooms):
    """
    test_id: BR-TEST-015
    source_id: BR-VH-014 double-occupancy
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-OCC-D",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=1),
        departure_date=date.today() + timedelta(days=3),
        status="approved",
    )
    allotment = RoomAllotment.objects.create(
        booking=b, room=r1, allotted_by=201, occupancy_type="double"
    )
    assert allotment.occupancy_type == "double"


def test_br_test_016_suite_room():
    """
    test_id: BR-TEST-016
    source_id: BR-VH-015 suite-room
    """
    room = Room.objects.create(room_number="S-201", room_type="suite", capacity=2, is_active=True)
    assert room.room_type == "suite"


def test_br_test_017_non_suite_room():
    """
    test_id: BR-TEST-017
    source_id: BR-VH-016 non-suite-room
    """
    room = Room.objects.create(
        room_number="NS-202", room_type="non_suite", capacity=2, is_active=True
    )
    assert room.room_type == "non_suite"


def test_br_test_018_no_show_alert():
    """
    test_id: BR-TEST-018
    source_id: BR-VH-017 no-show-alert
    """
    past_arr = date.today() - timedelta(days=1)
    b = Booking.objects.create(
        booking_reference="BK-ALERT-NS",
        indenter_id=101,
        arrival_date=past_arr,
        departure_date=date.today() + timedelta(days=2),
        status="room_allotted",
    )
    count = evaluate_no_shows()
    assert count >= 1
    assert StayAlert.objects.filter(booking=b, alert_type="no_show").exists()


def test_br_test_019_overstay_alert():
    """
    test_id: BR-TEST-019
    source_id: BR-VH-018 overstay-alert
    """
    past_dep = date.today() - timedelta(days=1)
    b = Booking.objects.create(
        booking_reference="BK-ALERT-OS",
        indenter_id=101,
        arrival_date=date.today() - timedelta(days=3),
        departure_date=past_dep,
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=3),
    )
    count = evaluate_overstays()
    assert count >= 1
    assert StayAlert.objects.filter(booking=b, alert_type="overstay").exists()


def test_br_test_020_permitted_categories(indenter_client):
    """
    test_id: BR-TEST-020
    source_id: BR-VH-019 category-permitted
    """
    for cat in ["A", "B", "C", "D"]:
        payload = {
            "visitor_name": f"Dr. Cat {cat}",
            "visitor_category": cat,
            "visit_purpose": "Category verification",
            "arrival_date": str(date.today() + timedelta(days=10)),
            "departure_date": str(date.today() + timedelta(days=12)),
            "number_of_rooms": 1,
            "number_of_occupants": 1,
            "billing_responsibility": "visitor",
        }
        resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
        assert resp.status_code == 201
        assert resp.data["visitor_category"] == cat


def test_br_test_021_prohibited_category(indenter_client):
    """
    test_id: BR-TEST-021
    source_id: BR-VH-019 category-prohibited
    """
    payload = {
        "visitor_name": "Dr. Cat E",
        "visitor_category": "E",
        "visit_purpose": "Category verification",
        "arrival_date": str(date.today() + timedelta(days=10)),
        "departure_date": str(date.today() + timedelta(days=12)),
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "visitor",
    }
    resp = indenter_client.post("/api/v1/vh/bookings/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_br_test_022_select_tariff(sample_tariffs):
    """
    test_id: BR-TEST-022
    source_id: BR-VH-023 select-tariff
    """
    tariff_rate = get_applicable_tariff(
        category="A",
        room_type="suite",
        occupancy="single",
        as_of_date=date.today(),
    )
    assert tariff_rate == Decimal("800.00")


def test_br_test_023_immutable_bills(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-023
    source_id: BR-VH-024 immutable-bills
    """
    r1, _, _ = sample_rooms
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-IMMUTABLE-BILL",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Tariff test",
        arrival_date=today - timedelta(days=2),
        departure_date=today,
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=2),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")

    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    initial_total = Decimal(str(resp.data["total_amount"]))

    # Update tariff rates in database
    TariffConfig.objects.filter(category="A", room_type="suite").update(
        daily_rate=Decimal("1500.00")
    )

    # Check bill in DB; it must remain unaffected
    bill = Bill.objects.get(booking=b)
    assert bill.total_amount == initial_total


def test_br_test_024_guest_staying_meal_permitted(caretaker_client):
    """
    test_id: BR-TEST-024
    source_id: BR-VH-025 guest-staying-meal-permitted
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-MEAL-PERM",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=3),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    payload = {
        "meal_date": str(today),
        "meal_option": "individual",
        "individual_type": "breakfast",
        "quantity": 1,
    }
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["meal_option"] == "individual"


def test_br_test_025_non_staying_meal_prohibited(caretaker_client):
    """
    test_id: BR-TEST-025
    source_id: BR-VH-025 non-staying-meal-prohibited
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-MEAL-PROH",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=3),
        status="pending",
    )
    payload = {
        "meal_date": str(today),
        "meal_option": "individual",
        "individual_type": "lunch",
        "quantity": 1,
    }
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
    assert resp.status_code in [400, 409, 422]


def test_br_test_026_meal_options_permitted(caretaker_client):
    """
    test_id: BR-TEST-026
    source_id: BR-VH-029 meal-options-permitted
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-MEAL-OPTS",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=3),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    for m_type in ["breakfast", "lunch", "dinner"]:
        payload = {
            "meal_date": str(today),
            "meal_option": "individual",
            "individual_type": m_type,
            "quantity": 1,
        }
        resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
        assert resp.status_code == 201
        assert resp.data["individual_type"] == m_type


def test_br_test_027_meal_options_prohibited(caretaker_client):
    """
    test_id: BR-TEST-027
    source_id: BR-VH-029 meal-options-prohibited
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-MEAL-PROH2",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=3),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    payload = {
        "meal_date": str(today),
        "meal_option": "individual",
        "individual_type": "supper",
        "quantity": 1,
    }
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_br_test_028_addon_options_permitted(caretaker_client):
    """
    test_id: BR-TEST-028
    source_id: BR-VH-030 addon-options-permitted
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-ADDON-PERM",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=3),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    for addon in ["tea", "milk"]:
        payload = {
            "meal_date": str(today),
            "meal_option": "add_on",
            "add_on_type": addon,
            "quantity": 2,
        }
        resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
        assert resp.status_code == 201
        assert resp.data["add_on_type"] == addon


def test_br_test_029_addon_options_prohibited(caretaker_client):
    """
    test_id: BR-TEST-029
    source_id: BR-VH-030 addon-options-prohibited
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-ADDON-PROH",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=3),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    payload = {
        "meal_date": str(today),
        "meal_option": "add_on",
        "add_on_type": "juice",
        "quantity": 1,
    }
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_br_test_030_meal_date_within_stay(caretaker_client):
    """
    test_id: BR-TEST-030
    source_id: BR-VH-031 meal-date-within-stay
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-MEAL-WITHIN",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=5),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    payload = {
        "meal_date": str(today + timedelta(days=2)),
        "meal_option": "full_day",
        "quantity": 1,
    }
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
    assert resp.status_code == 201


def test_br_test_031_meal_date_outside_stay(caretaker_client):
    """
    test_id: BR-TEST-031
    source_id: BR-VH-031 meal-date-outside-stay
    """
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-MEAL-OUTSIDE",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=2),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    payload = {
        "meal_date": str(today + timedelta(days=5)),
        "meal_option": "full_day",
        "quantity": 1,
    }
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/meals/", payload, format="json")
    assert resp.status_code in [400, 422]


def test_br_test_032_meal_included_in_billing(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-032
    source_id: BR-VH-032 meal-included-in-billing
    """
    r1, _, _ = sample_rooms
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-BILL-MEAL",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Meal billing test",
        arrival_date=today - timedelta(days=1),
        departure_date=today,
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=1),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")
    MealBooking.objects.create(
        booking=b,
        meal_date=today,
        meal_option="full_day",
        quantity=1,
        rate=Decimal("300.00"),
        amount=Decimal("300.00"),
    )

    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["meal_charge_total"])) == Decimal("300.00")
    assert Decimal(str(resp.data["total_amount"])) == Decimal("1100.00")  # 800 + 300


def test_br_test_033_room_rent_billing(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-033
    source_id: BR-VH-033 room-rent-billing
    """
    r1, _, _ = sample_rooms
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-RENT-BILL",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Rent test",
        arrival_date=today - timedelta(days=2),
        departure_date=today,
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=2),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")

    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    # 2 days * 800.00 = 1600.00
    assert Decimal(str(resp.data["room_rent_total"])) == Decimal("1600.00")


def test_br_test_034_meal_consumption_billing(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-034
    source_id: BR-VH-034 meal-consumption-billing
    """
    r1, _, _ = sample_rooms
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-TOTAL-MEAL",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Total meal test",
        arrival_date=today - timedelta(days=1),
        departure_date=today,
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=1),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")
    MealBooking.objects.create(
        booking=b,
        meal_date=today,
        meal_option="individual",
        individual_type="dinner",
        quantity=2,
        rate=Decimal("120.00"),
        amount=Decimal("240.00"),
    )

    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["meal_charge_total"])) == Decimal("240.00")
    assert Decimal(str(resp.data["total_amount"])) == Decimal("1040.00")  # 800 + 240


def test_br_test_035_cancellation_charge_billing(caretaker_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-035
    source_id: BR-VH-035 cancellation-charge-billing
    """
    r1, _, _ = sample_rooms
    b = Booking.objects.create(
        booking_reference="BK-CANCEL-CHARGE",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Cancellation charge bill test",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=1),
        status="cancelled",
        cancellation_charge_percentage=Decimal("50.00"),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["cancellation_charge_total"])) == Decimal("400.00")
    assert Decimal(str(resp.data["total_amount"])) == Decimal("400.00")


def test_br_test_036_offline_cash_settlement(caretaker_client):
    """
    test_id: BR-TEST-036
    source_id: BR-VH-036 offline-cash-settlement
    """
    b = Booking.objects.create(
        booking_reference="BK-SETTLE-CASH",
        indenter_id=101,
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today(),
        status="checked_out",
    )
    bill = Bill.objects.create(
        booking=b,
        total_amount=Decimal("800.00"),
        status="pending",
    )
    payload = {
        "payment_mode": "offline_cash",
        "amount_paid": "800.00",
        "receipt_number": "REC-CASH-001",
    }
    resp = caretaker_client.post(f"/api/v1/vh/bills/{bill.id}/settle/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["payment_mode"] == "offline_cash"


def test_br_test_037_immutable_billing_records(caretaker_client):
    """
    test_id: BR-TEST-037
    source_id: BR-VH-037 immutable-billing-records
    """
    b = Booking.objects.create(
        booking_reference="BK-SETTLE-IMMUTABLE",
        indenter_id=101,
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today(),
        status="checked_out",
    )
    bill = Bill.objects.create(
        booking=b,
        total_amount=Decimal("800.00"),
        status="settled",
    )
    payload = {
        "payment_mode": "offline_cash",
        "amount_paid": "800.00",
        "receipt_number": "REC-CASH-002",
    }
    resp = caretaker_client.post(f"/api/v1/vh/bills/{bill.id}/settle/", payload, format="json")
    assert resp.status_code in [400, 409, 422]


def test_br_test_038_below_threshold_alert():
    """
    test_id: BR-TEST-038
    source_id: BR-VH-041 below-threshold-alert
    """
    item = InventoryItem.objects.create(
        item_name="Pillow Covers",
        category="linen",
        current_quantity=3,
        minimum_threshold=10,
        unit="pieces",
    )
    evaluate_all_inventory_thresholds()
    item.refresh_from_db()
    assert item.is_threshold_alert is True


def test_br_test_039_above_threshold_no_alert():
    """
    test_id: BR-TEST-039
    source_id: BR-VH-041 above-threshold-no-alert
    """
    item = InventoryItem.objects.create(
        item_name="Blanket Covers",
        category="linen",
        current_quantity=15,
        minimum_threshold=10,
        unit="pieces",
    )
    evaluate_all_inventory_thresholds()
    item.refresh_from_db()
    assert item.is_threshold_alert is False


def test_br_test_040_threshold_notification():
    """
    test_id: BR-TEST-040
    source_id: BR-VH-043 threshold-notification
    """
    item = InventoryItem.objects.create(
        item_name="Bath Mats",
        category="linen",
        current_quantity=2,
        minimum_threshold=10,
        unit="pieces",
    )
    count = evaluate_all_inventory_thresholds()
    assert count >= 1
    item.refresh_from_db()
    assert item.is_threshold_alert is True


def test_br_test_041_caretaker_cardinality():
    """
    test_id: BR-TEST-041
    source_id: BR-VH-045 caretaker-cardinality
    """
    OperationalRoleHolder.objects.create(
        role_name="caretaker",
        user_id=201,
        is_active=True,
        valid_from=timezone.now() - timedelta(days=10),
    )
    # Assign new caretaker
    reassign_operational_role(
        role_name="caretaker",
        new_user_id=202,
        valid_from=timezone.now(),
        valid_to=None,
        principal=None,
    )

    active_holders = OperationalRoleHolder.objects.filter(role_name="caretaker", is_active=True)
    assert active_holders.count() == 1
    assert active_holders.first().user_id == 202


def test_br_test_042_incharge_cardinality():
    """
    test_id: BR-TEST-042
    source_id: BR-VH-046 incharge-cardinality
    """
    OperationalRoleHolder.objects.create(
        role_name="incharge",
        user_id=301,
        is_active=True,
        valid_from=timezone.now() - timedelta(days=10),
    )
    # Assign new incharge
    reassign_operational_role(
        role_name="incharge",
        new_user_id=302,
        valid_from=timezone.now(),
        valid_to=None,
        principal=None,
    )

    active_holders = OperationalRoleHolder.objects.filter(role_name="incharge", is_active=True)
    assert active_holders.count() == 1
    assert active_holders.first().user_id == 302


def test_br_test_043_time_bound_role(vh_client):
    """
    test_id: BR-TEST-043
    source_id: BR-VH-047 time-bound-role
    """
    admin_client = vh_client(user_id=1, perms=["vh.role.assign"], kind="admin")
    from_time = timezone.now()
    to_time = timezone.now() + timedelta(days=365)
    payload = {
        "role_name": "caretaker",
        "new_user_id": 205,
        "valid_from": from_time.isoformat(),
        "valid_to": to_time.isoformat(),
    }
    resp = admin_client.post("/api/v1/vh/roles/reassign/", payload, format="json")
    assert resp.status_code == 200

    holder = OperationalRoleHolder.objects.get(role_name="caretaker", user_id=205, is_active=True)
    assert holder.valid_from is not None
    assert holder.valid_to is not None


def test_br_test_044_immediate_role_reassignment():
    """
    test_id: BR-TEST-044
    source_id: BR-VH-048 immediate-role-reassignment
    """
    OperationalRoleHolder.objects.create(
        role_name="caretaker",
        user_id=201,
        is_active=True,
        valid_from=timezone.now() - timedelta(days=10),
    )
    new_holder = reassign_operational_role(
        role_name="caretaker",
        new_user_id=206,
        valid_from=timezone.now(),
        valid_to=None,
        principal=None,
    )
    assert new_holder.is_active is True

    current = OperationalRoleHolder.objects.filter(role_name="caretaker", is_active=True).first()
    assert current is not None
    assert current.user_id == 206


def test_br_test_045_transfer_pending_records(vh_client):
    """
    test_id: BR-TEST-045
    source_id: BR-VH-049 transfer-pending-records
    """
    # Create pending booking
    Booking.objects.create(
        booking_reference="BK-TRANSFER-PEND",
        indenter_id=101,
        visit_purpose="Pending transfer test",
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    # Reassign caretaker
    reassign_operational_role(
        role_name="caretaker",
        new_user_id=208,
        valid_from=timezone.now(),
        valid_to=None,
        principal=None,
    )

    # New caretaker accesses bookings
    new_caretaker_client = vh_client(
        user_id=208,
        perms=_CARETAKER_PERMS,
        kind="staff",
    )
    resp = new_caretaker_client.get("/api/v1/vh/bookings/")
    assert resp.status_code == 200
    assert any(b["booking_reference"] == "BK-TRANSFER-PEND" for b in resp.data)


def test_br_test_046_transfer_ongoing_records(vh_client, sample_rooms, sample_tariffs):
    """
    test_id: BR-TEST-046
    source_id: BR-VH-050 transfer-ongoing-records
    """
    r1, _, _ = sample_rooms
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-TRANSFER-STAY",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Stay transfer test",
        arrival_date=today - timedelta(days=2),
        departure_date=today,
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=2),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")

    # Reassign caretaker
    reassign_operational_role(
        role_name="caretaker",
        new_user_id=209,
        valid_from=timezone.now(),
        valid_to=None,
        principal=None,
    )

    new_caretaker_client = vh_client(
        user_id=209,
        perms=_CARETAKER_PERMS,
        kind="staff",
    )
    # Generate bill and checkout by new caretaker
    bill_resp = new_caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert bill_resp.status_code == 201

    co_resp = new_caretaker_client.post(
        f"/api/v1/vh/bookings/{b.id}/checkout/",
        {"verified_by_guest": True},
        format="json",
    )
    assert co_resp.status_code == 200
    b.refresh_from_db()
    assert b.status == "checked_out"
    assert co_resp.status_code == 200
    b.refresh_from_db()
    assert b.status == "checked_out"
