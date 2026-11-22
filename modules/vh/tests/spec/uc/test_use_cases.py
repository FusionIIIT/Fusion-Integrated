"""Use-case tests generated from the frozen UC_DESIGN.json."""
from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.vh.models import (
    Bill,
    BookingStatus,
    InventoryItem,
    RoomAllotment,
    Tariff,
    VHAlert,
    VHMSUserRole,
    VHNotificationLog,
)
from modules.vh.tests.spec.fr.test_helpers import case_id, load_design, make_booking, post_booking


@pytest.mark.django_db
@pytest.mark.parametrize("case", load_design("UC"), ids=case_id)
def test_uc_flow(case, api_client, category_a, sample_room):
    """Each test item retains the frozen test_id and source_id in its pytest ID."""
    source = case["source_id"]
    uid = re.search(r"UC-VH-\d{3}", source).group()
    number = int(uid[-3:])
    today = timezone.localdate()
    flow = "MAIN" if "Main Flow" in source else "ALT" if "Alternative Flow" in source else "EXC"
    alt_no_match = re.search(r"(?:Alternative|Exception) Flow (\d+)", source)
    alt_no = int(alt_no_match.group(1)) if alt_no_match else 0

    if number == 1:
        if flow == "MAIN":
            response = post_booking(api_client, category_a.id)
            assert response.status_code == 201
            assert response.data["status"] == BookingStatus.PENDING
            assert VHNotificationLog.objects.filter(booking_id=response.data["id"], event_type="BOOKING_SUBMITTED").exists()
        elif alt_no == 1:
            payload = {"indenter_id": 1, "visitor_category": category_a.id, "visit_purpose": "Incomplete", "check_in_date": str(today + timedelta(days=3)), "check_out_date": str(today + timedelta(days=4)), "billing_responsibility": "VISITOR"}
            response = api_client.post("/api/v1/vh/bookings/", payload, format="json")
            assert response.status_code == 400
        else:
            response = post_booking(api_client, category_a.id, billing_responsibility="UNLISTED")
            assert response.status_code == 400
        return

    if number == 2:
        if alt_no == 1:
            response = api_client.get("/api/v1/vh/bookings/?indenter_id=991002")
            rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
            assert response.status_code == 200 and rows == []
        else:
            booking = make_booking(category_a)
            listing = api_client.get(f"/api/v1/vh/bookings/?indenter_id={booking.indenter_id}")
            rows = listing.data.get("results", listing.data) if isinstance(listing.data, dict) else listing.data
            assert any(row["id"] == booking.id for row in rows)
            detail = api_client.get(f"/api/v1/vh/bookings/{booking.id}/")
            printable = api_client.get(f"/api/v1/vh/bookings/{booking.id}/printable/")
            assert detail.status_code == printable.status_code == 200
            assert printable.data["booking_reference"] == booking.booking_reference
        return

    if number == 3:
        booking = make_booking(category_a)
        available = api_client.get(f"/api/v1/vh/rooms/availability/?check_in={booking.check_in_date}&check_out={booking.check_out_date}")
        assert available.status_code == 200
        if "Alternative Flow 1" in source:
            route = api_client.post(f"/api/v1/vh/bookings/{booking.id}/reject/", {}, format="json")
            assert route.status_code == 200 and route.data["status"] == BookingStatus.REJECTED
        else:
            route = api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/", {}, format="json")
            assert route.status_code == 200 and route.data["status"] == BookingStatus.FORWARDED
        return

    if number == 4:
        booking = make_booking(category_a)
        api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/", {}, format="json")
        decision = "approve" if flow == "MAIN" or alt_no == 1 else "reject"
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/{decision}/", {}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == (BookingStatus.APPROVED if decision == "approve" else BookingStatus.REJECTED)
        assert VHNotificationLog.objects.filter(booking=booking).exists()
        return

    if number == 5:
        extra = {} if flow == "MAIN" else {"visitor_name": ""}
        response = post_booking(api_client, category_a.id, is_offline=True, offline_booking_type="TELEPHONIC", **extra)
        if flow == "MAIN":
            assert response.status_code == 201
            assert response.data["is_offline"] is True and response.data["status"] == BookingStatus.PENDING
        else:
            assert response.status_code == 400
        return

    if number == 6:
        booking = make_booking(category_a, days=10 if flow == "MAIN" else -1)
        response = api_client.post("/api/v1/vh/modifications/", {"booking": booking.id, "new_number_of_rooms": 2, "reason": "Update request"}, format="json")
        if flow == "MAIN":
            assert response.status_code == 201
            assert response.data["status"] == "PENDING"
            assert VHNotificationLog.objects.filter(booking=booking, event_type="MODIFICATION_REQUESTED").exists()
        else:
            booking.status = BookingStatus.CHECKED_IN
            booking.save()
            response = api_client.post("/api/v1/vh/modifications/", {"booking": booking.id, "new_number_of_rooms": 2, "reason": "Late update"}, format="json")
            assert response.status_code == 400
        return

    if number == 7:
        days = 7 if alt_no == 1 else 3 if alt_no == 2 or flow == "MAIN" else 0
        booking = make_booking(category_a, days=days)
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
        assert response.status_code == 200
        expected = Decimal("0.00") if days == 7 else Decimal("250.00") if days > 0 else Decimal("500.00")
        assert Decimal(response.data["applicable_cancellation_charge"]) == expected
        return

    if number == 8:
        booking = make_booking(category_a)
        if flow == "MAIN":
            booking.status = BookingStatus.APPROVED
            booking.save()
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/allot_room/", {"room_ids": [sample_room.id]}, format="json")
            assert response.status_code == 200 and response.data["booking"]["status"] == BookingStatus.ROOM_ALLOTTED
        else:
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/allot_room/", {"room_ids": [sample_room.id]}, format="json")
            assert response.status_code == 400
            assert RoomAllotment.objects.filter(booking=booking).count() == 0
        return

    if number == 9:
        booking = make_booking(category_a, status=BookingStatus.ROOM_ALLOTTED)
        RoomAllotment.objects.create(booking=booking, room=sample_room)
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_in/", {}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == BookingStatus.CHECKED_IN
        assert response.data["allotments"][0]["check_in_time"] is not None
        return

    if number == 11:
        cat = api_client.post("/api/v1/vh/categories/", {"code": "A", "name": "Category A"}, format="json")
        if cat.status_code != 201:
            cat = api_client.get("/api/v1/vh/categories/")
            rows = cat.data.get("results", cat.data) if isinstance(cat.data, dict) else cat.data
            cat_id = next(row["id"] for row in rows if row["code"] == "A")
        else:
            cat_id = cat.data["id"]
        response = api_client.post("/api/v1/vh/tariffs/", {"category": cat_id, "room_type": "SUITE", "occupancy_type": "SINGLE", "rate_per_day": "800.00", "effective_from": str(today)}, format="json")
        assert response.status_code == 201
        return

    if number == 12:
        booking = make_booking(category_a, status=BookingStatus.CHECKED_IN, days=0)
        if flow == "MAIN":
            response = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date), "meal_type": "FULL_DAY", "add_on": "TEA", "rate": "100.00"}, format="json")
            assert response.status_code == 201
            assert response.data["booking"] == booking.id
        else:
            response = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_out_date + timedelta(days=1)), "meal_type": "LUNCH", "rate": "100.00"}, format="json")
            assert response.status_code == 400
        return

    if number == 13:
        booking = make_booking(category_a, status=BookingStatus.CHECKED_IN, days=0, stay=2)
        RoomAllotment.objects.create(booking=booking, room=sample_room, check_in_time=timezone.now())
        if flow == "MAIN":
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {"guest_verification_notes": "Verified"}, format="json")
            assert response.status_code == 200 and response.data["bill"]["total_amount"] is not None
        elif alt_no == 1:
            booking.status = BookingStatus.ROOM_ALLOTTED
            booking.check_in_date = today
            booking.save()
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/record_no_show/", {}, format="json")
            assert response.status_code == 200
            assert Decimal(response.data["bill"]["cancellation_charges"]) > 0
        else:
            api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
            bill = Bill.objects.get(booking=booking)
            before = bill.total_amount
            Tariff.objects.filter(category=category_a).update(rate_per_day=Decimal("9999.00"))
            bill.refresh_from_db()
            assert bill.total_amount == before
        return

    if number == 14:
        response = api_client.post("/api/v1/vh/inventory/", {"name": "UC-inventory-main", "category": "LINEN", "current_quantity": 2, "minimum_threshold": 5}, format="json")
        assert response.status_code == 201
        assert response.data["is_below_threshold"] is True
        assert VHAlert.objects.filter(inventory_item_id=response.data["id"], alert_type="INVENTORY_THRESHOLD").exists()
        return

    if number == 15:
        item = InventoryItem.objects.create(name="UC-replenishment", category="LINEN", current_quantity=2, minimum_threshold=5)
        replenishment = api_client.post(f"/api/v1/vh/inventory/{item.id}/request_replenishment/", {"quantity_requested": 3}, format="json")
        assert replenishment.status_code == 201
        approved = api_client.post(f"/api/v1/vh/replenishments/{replenishment.data['id']}/approve/", {}, format="json")
        assert approved.status_code == 200 and approved.data["status"] == "APPROVED"
        return

    if number == 17:
        response = api_client.get("/api/v1/vh/reports/incharge/")
        assert response.status_code == 200
        assert {"booking_summary", "category_occupancy", "revenue_summary", "inventory_usage"} <= set(response.data)
        return

    if number == 18:
        response = api_client.get("/api/v1/vh/reports/caretaker/")
        assert response.status_code == 200
        assert {"daily_occupancy", "upcoming_arrivals", "upcoming_departures", "pending_actions", "no_show_logs", "overstay_logs"} <= set(response.data)
        return

    if number == 19:
        role = VHMSUserRole.reassign_role("CARETAKER", 8019, start_date=today)
        booking = make_booking(category_a)
        VHMSUserRole.reassign_role("CARETAKER", 8020, start_date=today)
        role.refresh_from_db()
        booking.refresh_from_db()
        assert role.is_active is False
        assert booking.assigned_caretaker_id == 8020
        return

    if number == 20:
        booking = make_booking(category_a, days=3)
        api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/", {}, format="json")
        assert response.status_code == 200 and response.data["booking"]["status"] == BookingStatus.CANCELLED
        return

    if number == 21:
        booking = make_booking(category_a, status=BookingStatus.CHECKED_IN, days=0)
        RoomAllotment.objects.create(booking=booking, room=sample_room, check_in_time=timezone.now())
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {"guest_verification_notes": "Bill checked with guest"}, format="json")
        assert response.status_code == 200
        assert response.data["booking"]["status"] == BookingStatus.CHECKED_OUT
        assert response.data["bill"]["guest_verification_notes"] == "Bill checked with guest"
        return

    if number == 22:
        booking = make_booking(category_a, days=10)
        mod = api_client.post("/api/v1/vh/modifications/", {"booking": booking.id, "new_number_of_rooms": 2, "reason": "Confirmed date/room change"}, format="json")
        assert mod.status_code == 201
        response = api_client.post(f"/api/v1/vh/modifications/{mod.data['id']}/confirm/", {}, format="json")
        assert response.status_code == 200 and response.data["status"] == "CONFIRMED"
        return

    if number == 23:
        if flow == "MAIN":
            booking = make_booking(category_a)
            assert VHNotificationLog.objects.filter(booking=booking).exists() or api_client.post("/api/v1/vh/bookings/", {"indenter_id": 1, "visitor_name": "UC-notify", "visitor_email": "uc@example.test", "visitor_category": category_a.id, "visit_purpose": "Notify", "check_in_date": str(today + timedelta(days=2)), "check_out_date": str(today + timedelta(days=4)), "billing_responsibility": "VISITOR"}, format="json").status_code == 201
            assert VHNotificationLog.objects.filter(event_type="BOOKING_SUBMITTED").exists()
        else:
            booking = make_booking(category_a)
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
            assert response.status_code == 200
            log = VHNotificationLog.objects.get(booking=booking, event_type="CANCELLATION_REQUESTED")
            assert log.subject and log.body
        return

    if number == 24:
        if flow == "MAIN":
            no_show = make_booking(category_a, status=BookingStatus.ROOM_ALLOTTED, days=-1)
            overstay = make_booking(category_a, status=BookingStatus.CHECKED_IN, days=-3, stay=1)
            RoomAllotment.objects.create(booking=no_show, room=sample_room)
            room2 = type(sample_room).objects.create(room_number="UC24-2", room_type=sample_room.room_type, occupancy_type=sample_room.occupancy_type, floor=1)
            RoomAllotment.objects.create(booking=overstay, room=room2, check_in_time=timezone.now())
            response = api_client.post("/api/v1/vh/alerts/scan/", {}, format="json")
            assert response.status_code == 200
            assert VHAlert.objects.filter(booking=no_show, alert_type="NO_SHOW").exists()
            assert VHAlert.objects.filter(booking=overstay, alert_type="OVERSTAY").exists()
        elif alt_no == 1:
            booking = make_booking(category_a, status=BookingStatus.ROOM_ALLOTTED, days=-1)
            RoomAllotment.objects.create(booking=booking, room=sample_room, check_in_time=timezone.now())
            api_client.post("/api/v1/vh/alerts/scan/", {}, format="json")
            assert not VHAlert.objects.filter(booking=booking, alert_type="NO_SHOW").exists()
        else:
            booking = make_booking(category_a, status=BookingStatus.CHECKED_IN, days=-3, stay=3)
            RoomAllotment.objects.create(booking=booking, room=sample_room, check_in_time=timezone.now(), check_out_time=timezone.now())
            api_client.post("/api/v1/vh/alerts/scan/", {}, format="json")
            assert not VHAlert.objects.filter(booking=booking, alert_type="OVERSTAY").exists()
        return

    if number == 25:
        quantity = 1 if flow == "MAIN" else 5
        item = InventoryItem.objects.create(name=f"UC-threshold-{flow}-{alt_no}", category="LINEN", current_quantity=quantity, minimum_threshold=5)
        response = api_client.post("/api/v1/vh/alerts/scan/", {}, format="json")
        assert response.status_code == 200
        if flow == "MAIN":
            assert VHAlert.objects.filter(inventory_item=item, alert_type="INVENTORY_THRESHOLD").exists()
            assert VHNotificationLog.objects.filter(event_type="INVENTORY_THRESHOLD").exists()
        else:
            assert not VHAlert.objects.filter(inventory_item=item, alert_type="INVENTORY_THRESHOLD").exists()
        return

    raise AssertionError(f"No use-case flow implementation for {uid} {source}")
