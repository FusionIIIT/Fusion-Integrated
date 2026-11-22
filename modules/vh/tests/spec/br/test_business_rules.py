"""Business-rule tests generated from frozen BR_DESIGN.json."""
from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.vh.models import (
    Bill,
    Booking,
    BookingStatus,
    MealBooking,
    RoomAllotment,
    Tariff,
    VHAlert,
    VHMSUserRole,
    VHMSUserRoleType,
    VHNotificationLog,
)
from modules.vh.tests.spec.fr.test_helpers import case_id, load_design, make_booking, post_booking


@pytest.mark.django_db
@pytest.mark.parametrize("case", load_design("BR"), ids=case_id)
def test_business_rule(case, api_client, all_categories, all_room_combinations, sample_room):
    """Each test item retains the frozen test_id and source_id in its pytest ID."""
    rule = re.search(r"BR-VH-\d{3}", case["source_id"]).group()
    n = int(rule[-3:])
    today = timezone.localdate()
    category = all_categories[0]

    if n == 2:
        for value in ("VISITOR", "INDENTER", "INSTITUTE", "PROJECT"):
            response = post_booking(api_client, category.id, billing_responsibility=value)
            assert response.status_code == 201
            assert response.data["billing_responsibility"] == value
        before = Booking.objects.count()
        refused = post_booking(api_client, category.id, billing_responsibility="UNSUPPORTED")
        assert refused.status_code == 400 and Booking.objects.count() == before
        return

    if n in (3, 4, 5):
        online = post_booking(api_client, category.id)
        offline = post_booking(api_client, category.id, is_offline=True, offline_booking_type="WALK_IN")
        assert online.status_code == offline.status_code == 201
        if n == 3:
            online_route = api_client.post(f"/api/v1/vh/bookings/{online.data['id']}/forward/", {}, format="json")
            offline_route = api_client.post(f"/api/v1/vh/bookings/{offline.data['id']}/forward/", {}, format="json")
            assert online_route.data["status"] == offline_route.data["status"] == BookingStatus.FORWARDED
        elif n == 4:
            online_avail = api_client.get("/api/v1/vh/rooms/availability/")
            offline_avail = api_client.get("/api/v1/vh/rooms/availability/")
            assert online_avail.status_code == offline_avail.status_code == 200
            assert {r["id"] for r in online_avail.data} == {r["id"] for r in offline_avail.data}
        else:
            assert offline.data["is_offline"] is True
            assert offline.data["offline_booking_type"] == "WALK_IN"
        return

    if n in (6, 7, 8, 9):
        days = {7: 7, 8: 3, 9: 0}.get(n, 3)
        if n == 6:
            for days, expected in ((7, Decimal("0.00")), (3, Decimal("250.00")), (0, Decimal("500.00"))):
                booking = make_booking(category, days=days)
                response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
                assert response.status_code == 200
                assert Decimal(response.data["applicable_cancellation_charge"]) == expected
        else:
            booking = make_booking(category, days=days)
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
            assert response.status_code == 200
            expected = {7: Decimal("0.00"), 8: Decimal("250.00"), 9: Decimal("500.00")}[n]
            assert Decimal(response.data["applicable_cancellation_charge"]) == expected
        return

    if n == 10:
        booking = make_booking(category)
        bill = Bill.objects.create(booking=booking, room_charges=Decimal("100.00"), total_amount=Decimal("100.00"))
        mod = api_client.post("/api/v1/vh/modifications/", {"booking": booking.id, "new_number_of_rooms": 2, "reason": "Room update"}, format="json")
        assert mod.status_code == 201
        bill.refresh_from_db()
        before = bill.room_charges
        api_client.post(f"/api/v1/vh/modifications/{mod.data['id']}/confirm/", {}, format="json")
        bill.refresh_from_db()
        assert bill.room_charges != before
        return

    if n == 11:
        booking = make_booking(category, days=3)
        api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
        confirmed = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/", {}, format="json")
        assert confirmed.status_code == 200
        assert Decimal(confirmed.data["bill"]["cancellation_charges"]) == Decimal("250.00")
        return

    if n == 12:
        booking = make_booking(category)
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/allot_room/", {"room_ids": [sample_room.id]}, format="json")
        assert response.status_code == 400
        assert RoomAllotment.objects.filter(booking=booking).count() == 0
        return

    if 13 <= n <= 16:
        room_type = "SUITE" if n == 15 else "NON_SUITE"
        occupancy = "SINGLE" if n == 13 else "DOUBLE"
        response = api_client.post("/api/v1/vh/rooms/", {"room_number": f"BR{n:03}", "room_type": room_type, "occupancy_type": occupancy, "floor": 1, "status": "AVAILABLE"}, format="json")
        assert response.status_code == 201
        assert response.data["room_type"] == room_type and response.data["occupancy_type"] == occupancy
        return

    if n in (17, 18):
        status = BookingStatus.ROOM_ALLOTTED if n == 17 else BookingStatus.CHECKED_IN
        days = -1 if n == 17 else -3
        booking = make_booking(category, status=status, days=days, stay=1)
        RoomAllotment.objects.create(booking=booking, room=sample_room, check_in_time=timezone.now() if n == 18 else None)
        response = api_client.post("/api/v1/vh/alerts/scan/", {}, format="json")
        assert response.status_code == 200
        alert_type = "NO_SHOW" if n == 17 else "OVERSTAY"
        assert VHAlert.objects.filter(booking=booking, alert_type=alert_type).exists()
        return

    if n == 19:
        rows = api_client.get("/api/v1/vh/categories/").data
        rows = rows.get("results", rows) if isinstance(rows, dict) else rows
        assert {row["code"] for row in rows} >= {"A", "B", "C", "D"}
        return

    if n == 23:
        booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=1, stay=2)
        room = all_room_combinations[0]
        RoomAllotment.objects.create(booking=booking, room=room, check_in_time=timezone.now())
        for occ in ("SINGLE", "DOUBLE"):
            Tariff.objects.get_or_create(category=category, room_type=room.room_type, occupancy_type=occ, effective_from=booking.check_in_date, defaults={"rate_per_day": Decimal("800.00")})
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
        assert response.status_code == 200
        assert Decimal(response.data["bill"]["room_charges"]) > 0
        return

    if n == 24:
        booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=0, stay=2)
        RoomAllotment.objects.create(booking=booking, room=sample_room, check_in_time=timezone.now())
        api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
        bill = Bill.objects.get(booking=booking)
        original = bill.total_amount
        Tariff.objects.create(category=category, room_type=sample_room.room_type, occupancy_type=sample_room.occupancy_type, effective_from=today, rate_per_day=Decimal("9999.00"))
        bill.refresh_from_db()
        assert bill.total_amount == original
        return

    if n == 25:
        booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=0)
        allowed = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date), "meal_type": "LUNCH", "rate": "100.00"}, format="json")
        assert allowed.status_code == 201
        booking.status = BookingStatus.APPROVED
        booking.save()
        refused = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date), "meal_type": "LUNCH", "rate": "100.00"}, format="json")
        assert refused.status_code == 400
        return

    if n in (29, 30):
        booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=0)
        options = ("BREAKFAST", "LUNCH", "DINNER") if n == 29 else ("TEA", "MILK")
        for option in options:
            payload = {"booking": booking.id, "date": str(booking.check_in_date), "meal_type": option if n == 29 else "FULL_DAY", "add_on": "NONE" if n == 29 else option, "rate": "100.00"}
            response = api_client.post("/api/v1/vh/meals/", payload, format="json")
            assert response.status_code == 201
        invalid = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date), "meal_type": "BRUNCH", "add_on": "COFFEE", "rate": "100.00"}, format="json")
        assert invalid.status_code == 400
        return

    if n == 31:
        booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=0, stay=2)
        in_stay = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date + timedelta(days=1)), "meal_type": "LUNCH", "rate": "100.00"}, format="json")
        out_stay = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_out_date + timedelta(days=1)), "meal_type": "LUNCH", "rate": "100.00"}, format="json")
        assert in_stay.status_code == 201 and out_stay.status_code == 400
        return

    if n in (32, 33, 34, 35):
        booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=0, stay=2)
        RoomAllotment.objects.create(booking=booking, room=sample_room, check_in_time=timezone.now())
        if n == 32 or n == 34:
            MealBooking.objects.create(booking=booking, date=booking.check_in_date, meal_type="LUNCH", number_of_persons=1, rate=Decimal("100.00"), total_amount=Decimal("100.00"))
        if n == 35:
            booking.calculated_cancellation_charge = Decimal("250.00")
        response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
        assert response.status_code == 200
        if n == 32 or n == 34:
            assert Decimal(response.data["bill"]["meal_charges"]) == Decimal("100.00")
        elif n == 33:
            assert Decimal(response.data["bill"]["room_charges"]) > 0
        return

    if n in (36, 37):
        booking = make_booking(category)
        bill = Bill.objects.create(booking=booking, room_charges=Decimal("100.00"), total_amount=Decimal("100.00"))
        settled = api_client.post(f"/api/v1/vh/bills/{bill.id}/settle/", {"payment_mode": "CASH"}, format="json")
        assert settled.status_code == 200 and settled.data["payment_mode"] == "CASH"
        if n == 37:
            refused = api_client.put(f"/api/v1/vh/bills/{bill.id}/", {"booking": booking.id, "room_charges": "500.00", "meal_charges": "0.00", "cancellation_charges": "0.00", "total_amount": "500.00", "payment_mode": "CASH", "is_finalized": True}, format="json")
            assert refused.status_code == 400
        return

    if n == 41:
        below = api_client.post("/api/v1/vh/inventory/", {"name": "BR-below", "category": "LINEN", "current_quantity": 4, "minimum_threshold": 5}, format="json")
        equal = api_client.post("/api/v1/vh/inventory/", {"name": "BR-equal", "category": "LINEN", "current_quantity": 5, "minimum_threshold": 5}, format="json")
        above = api_client.post("/api/v1/vh/inventory/", {"name": "BR-above", "category": "LINEN", "current_quantity": 6, "minimum_threshold": 5}, format="json")
        assert below.status_code == equal.status_code == above.status_code == 201
        assert VHAlert.objects.filter(inventory_item_id=below.data["id"], alert_type="INVENTORY_THRESHOLD").exists()
        assert not VHAlert.objects.filter(inventory_item_id=equal.data["id"], alert_type="INVENTORY_THRESHOLD").exists()
        assert not VHAlert.objects.filter(inventory_item_id=above.data["id"], alert_type="INVENTORY_THRESHOLD").exists()
        return

    if n == 43:
        item = api_client.post("/api/v1/vh/inventory/", {"name": "BR-alert-mail", "category": "LINEN", "current_quantity": 1, "minimum_threshold": 5}, format="json")
        assert item.status_code == 201
        assert VHNotificationLog.objects.filter(event_type="INVENTORY_THRESHOLD").exists()
        return

    if n in (45, 46, 47, 48, 49, 50):
        role_type = VHMSUserRoleType.CARETAKER if n in (45, 47, 48, 49, 50) else VHMSUserRoleType.IN_CHARGE
        role = VHMSUserRole.reassign_role(role_type, 9000 + n, start_date=today, end_date=today + timedelta(days=30))
        assert role.is_active and role.start_date == today and role.end_date == today + timedelta(days=30)
        if n in (45, 46):
            assert VHMSUserRole.objects.filter(role_type=role_type, is_active=True).count() == 1
        elif n == 48:
            assert VHMSUserRole.get_active_caretaker().user_id == 9048
        elif n in (49, 50):
            state = BookingStatus.PENDING if n == 49 else BookingStatus.CHECKED_IN
            booking = make_booking(category, status=state)
            VHMSUserRole.reassign_role(role_type, 9100 + n, start_date=today)
            booking.refresh_from_db()
            assert booking.assigned_caretaker_id == 9100 + n
        return

    raise AssertionError(f"No business-rule test implementation for {rule}")
