"""Requirement tests generated from frozen FR_DESIGN.json."""
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
    InventoryItem,
    InventoryReplenishment,
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
@pytest.mark.parametrize("case", load_design("FR"), ids=case_id)
def test_fr_requirement_obligation(case, api_client, all_categories, all_room_combinations, all_tariffs):
    """Each pytest parameter ID carries the frozen test_id and exact source_id."""
    afr = re.search(r"AFR-VH-\d{3}", case["source_id"]).group()
    n = int(afr[-3:])
    today = timezone.localdate()
    category = all_categories[0]
    if n in (1, 2, 3):
        booking = make_booking(category)
        if n == 1:
            response = api_client.get(f"/api/v1/vh/bookings/?indenter_id={booking.indenter_id}")
            assert response.status_code == 200
            rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
            assert any(row["id"] == booking.id and row["status"] == BookingStatus.PENDING for row in rows)
            own = next(row for row in rows if row["id"] == booking.id)
            assert "history" in own or "status_history" in own
        elif n == 2:
            response = api_client.get(f"/api/v1/vh/bookings/{booking.id}/")
            assert response.status_code == 200
            assert response.data["visitor_name"] == booking.visitor_name
            assert response.data["booking_reference"] == booking.booking_reference
        else:
            response = api_client.get(f"/api/v1/vh/bookings/{booking.id}/printable/")
            assert response.status_code == 200
            assert response.data["booking_reference"] == booking.booking_reference
            assert response.data["billing_responsibility"] == booking.billing_responsibility
        return

    if 5 <= n <= 13:
        field_payload = {
            5: {},
            6: {"visitor_name": "Recorded Visitor", "visitor_email": "visitor@example.test", "visitor_phone": "+1-555-0100", "visitor_address": "Institute guest"},
            7: {"visit_purpose": "Research seminar"},
            8: {"visitor_category": category.id},
            9: {"check_in_date": str(today + timedelta(days=10)), "check_out_date": str(today + timedelta(days=12)), "expected_check_in_time": "14:00:00", "expected_check_out_time": "10:30:00"},
            10: {"number_of_rooms": 2, "number_of_occupants": 3},
            11: {"billing_responsibility": "PROJECT"},
            13: {},
        }
        if n == 12:
            for value in ("VISITOR", "INDENTER", "INSTITUTE", "PROJECT"):
                response = post_booking(api_client, category.id, billing_responsibility=value)
                assert response.status_code == 201
                assert response.data["billing_responsibility"] == value
            before = Booking.objects.count()
            invalid = post_booking(api_client, category.id, billing_responsibility="UNKNOWN")
            assert invalid.status_code == 400
            assert Booking.objects.count() == before
            return
        response = post_booking(api_client, category.id, **field_payload[n])
        assert response.status_code == 201
        if n == 5:
            assert response.data["status"] == BookingStatus.PENDING
        elif n == 6:
            assert response.data["visitor_name"] == "Recorded Visitor"
            assert response.data["visitor_email"] == "visitor@example.test"
        elif n == 7:
            assert response.data["visit_purpose"] == "Research seminar"
        elif n == 8:
            assert response.data["category_code"] == category.code
        elif n == 9:
            assert response.data["check_in_date"] == str(today + timedelta(days=10))
            assert response.data["expected_check_in_time"] == "14:00:00"
        elif n == 10:
            assert response.data["number_of_rooms"] == 2
            assert response.data["number_of_occupants"] == 3
        elif n == 11:
            assert response.data["billing_responsibility"] == "PROJECT"
        elif n == 13:
            assert response.data["status"] == BookingStatus.PENDING
        return

    if n in (14, 15, 16, 17, 18, 19, 20):
        booking = make_booking(category)
        if n == 14:
            response = api_client.get(f"/api/v1/vh/bookings/{booking.id}/")
            assert response.status_code == 200
            assert response.data["id"] == booking.id
        elif n == 15:
            response = api_client.get(
                f"/api/v1/vh/rooms/availability/?check_in={booking.check_in_date}&check_out={booking.check_out_date}"
            )
            assert response.status_code == 200
            assert any(row["id"] == all_room_combinations[0].id for row in response.data)
        elif n == 16:
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/reject/", {}, format="json")
            assert response.status_code == 200
            assert response.data["status"] == BookingStatus.REJECTED
        elif n in (17, 18, 19):
            forward = api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/", {}, format="json")
            assert forward.status_code == 200
            if n == 17:
                assert forward.data["status"] == BookingStatus.FORWARDED
            elif n == 18:
                response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/approve/", {}, format="json")
                assert response.status_code == 200
                assert response.data["status"] == BookingStatus.APPROVED
            else:
                response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/reject/", {}, format="json")
                assert response.status_code == 200
                assert response.data["status"] == BookingStatus.REJECTED
        else:
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/", {}, format="json")
            assert response.status_code == 200
            api_client.post(f"/api/v1/vh/bookings/{booking.id}/approve/", {}, format="json")
            assert VHNotificationLog.objects.filter(booking=booking).exists()
        return

    if n in (21, 22, 23, 24, 25):
        offline_kind = "TELEPHONIC" if n != 22 else "WALK_IN"
        response = post_booking(api_client, category.id, is_offline=True, offline_booking_type=offline_kind)
        assert response.status_code == 201
        booking_id = response.data["id"]
        assert response.data["is_offline"] is True
        assert response.data["offline_booking_type"] == offline_kind
        if n == 23:
            forwarded = api_client.post(f"/api/v1/vh/bookings/{booking_id}/forward/", {}, format="json")
            assert forwarded.status_code == 200
            assert forwarded.data["status"] == BookingStatus.FORWARDED
        elif n == 24:
            avail = api_client.get("/api/v1/vh/rooms/availability/")
            assert avail.status_code == 200
        elif n == 25:
            listing = api_client.get("/api/v1/vh/bookings/?is_offline=true")
            assert listing.status_code == 200
        return

    if n == 26:
        booking = make_booking(category)
        response = api_client.post("/api/v1/vh/modifications/", {"booking": booking.id, "new_number_of_rooms": 2, "reason": "Add a room"}, format="json")
        assert response.status_code == 201
        assert response.data["booking"] == booking.id
        return

    if 27 <= n <= 35:
        days = {28: 3, 29: 7, 30: 3, 31: 0, 32: 3, 33: 3, 34: 3, 35: 3}.get(n, 3)
        booking = make_booking(category, days=days)
        Tariff.objects.get_or_create(category=category, room_type="NON_SUITE", occupancy_type="DOUBLE", effective_from=booking.check_in_date, defaults={"rate_per_day": Decimal("1000.00")})
        if n == 28:
            for case_days, expected in ((7, Decimal("0.00")), (3, Decimal("250.00")), (0, Decimal("500.00"))):
                b = make_booking(category, days=case_days)
                got = api_client.post(f"/api/v1/vh/bookings/{b.id}/request_cancellation/", {}, format="json")
                assert got.status_code == 200
                assert Decimal(got.data["applicable_cancellation_charge"]) == expected
        elif n == 34:
            bill = Bill.objects.create(booking=booking, room_charges=Decimal("1000.00"), total_amount=Decimal("1000.00"))
            mod = api_client.post("/api/v1/vh/modifications/", {"booking": booking.id, "new_number_of_rooms": 2, "reason": "Add a room"}, format="json")
            assert mod.status_code == 201
            confirmed = api_client.post(f"/api/v1/vh/modifications/{mod.data['id']}/confirm/", {}, format="json")
            assert confirmed.status_code == 200
            bill.refresh_from_db()
            assert bill.room_charges == Decimal("4000.00")
        elif n in (27, 29, 30, 31, 32, 33):
            resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
            assert resp.status_code == 200
            expected = {29: Decimal("0.00"), 30: Decimal("250.00"), 31: Decimal("500.00")}.get(n)
            if expected is not None:
                assert Decimal(resp.data["applicable_cancellation_charge"]) == expected
            if n == 32:
                assert Booking.objects.get(pk=booking.id).status == BookingStatus.CANCELLATION_REQUESTED
            if n == 33:
                done = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/", {}, format="json")
                assert done.status_code == 200
                assert done.data["booking"]["status"] == BookingStatus.CANCELLED
        else:
            resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
            assert resp.status_code == 200
            done = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/", {}, format="json")
            assert done.status_code == 200
            assert Decimal(done.data["bill"]["cancellation_charges"]) == Decimal(resp.data["applicable_cancellation_charge"])
        return

    if n == 36:
        booking = make_booking(category)
        room = all_room_combinations[0]
        refused = api_client.post(f"/api/v1/vh/bookings/{booking.id}/allot_room/", {"room_ids": [room.id]}, format="json")
        assert refused.status_code == 400
        booking.status = BookingStatus.APPROVED
        booking.save()
        accepted = api_client.post(f"/api/v1/vh/bookings/{booking.id}/allot_room/", {"room_ids": [room.id]}, format="json")
        assert accepted.status_code == 200
        return

    if 37 <= n <= 40:
        room_type = "SUITE" if n == 39 else "NON_SUITE"
        occupancy = "SINGLE" if n == 37 else "DOUBLE"
        response = api_client.post("/api/v1/vh/rooms/", {"room_number": f"FR{n:03}", "room_type": room_type, "occupancy_type": occupancy, "floor": 1, "status": "AVAILABLE"}, format="json")
        assert response.status_code == 201
        assert response.data["room_type"] == room_type and response.data["occupancy_type"] == occupancy
        return

    if n in (41, 42, 43, 44):
        days = -1 if n in (43, 44) else 1
        state = BookingStatus.CHECKED_IN if n in (42, 44) else BookingStatus.ROOM_ALLOTTED
        booking = make_booking(category, status=state, days=days, stay=0 if n in (43,44) else 2)
        room = all_room_combinations[0]
        RoomAllotment.objects.create(booking=booking, room=room, check_in_time=timezone.now() if state == BookingStatus.CHECKED_IN else None)
        if n == 41:
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_in/", {}, format="json")
            assert response.status_code == 200
            assert response.data["allotments"][0]["check_in_time"] is not None
        elif n == 42:
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {"guest_verification_notes": "Checked"}, format="json")
            assert response.status_code == 200
            assert response.data["bill"]["guest_verification_notes"] == "Checked"
            assert response.data["booking"]["allotments"][0]["check_out_time"] is not None
        elif n in (43, 44):
            if n == 43:
                booking.check_in_date = today - timedelta(days=1)
                booking.save()
            else:
                booking.check_out_date = today - timedelta(days=1)
                booking.save()
            response = api_client.post("/api/v1/vh/alerts/scan/", {}, format="json")
            assert response.status_code == 200
            alert_type = "NO_SHOW" if n == 43 else "OVERSTAY"
            assert VHAlert.objects.filter(booking=booking, alert_type=alert_type).exists()
        return

    if n == 45:
        response = api_client.get("/api/v1/vh/categories/")
        assert response.status_code == 200
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        assert {r["code"] for r in rows} >= {"A", "B", "C", "D"}
        return

    if n in (46, 47, 48, 49, 50, 108):
        if n in (46, 47, 48):
            effective_from = today + timedelta(days=1)
            payload = {"category": category.id, "room_type": "SUITE" if n == 46 else "NON_SUITE", "occupancy_type": "SINGLE" if n == 47 else "DOUBLE", "rate_per_day": "750.00", "effective_from": str(effective_from)}
            response = api_client.post("/api/v1/vh/tariffs/", payload, format="json")
            assert response.status_code == 201
            assert response.data["rate_per_day"] == "750.00"
            if n == 48:
                assert response.data["effective_from"] == str(effective_from)
        else:
            booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=1, stay=2)
            room = all_room_combinations[0]
            RoomAllotment.objects.create(booking=booking, room=room, check_in_time=timezone.now())
            old, _ = Tariff.objects.get_or_create(category=category, room_type=room.room_type, occupancy_type=room.occupancy_type, effective_from=booking.check_in_date, defaults={"rate_per_day": Decimal("700.00")})
            if n == 49:
                api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
                bill = Bill.objects.get(booking=booking)
                assert bill.room_charges == old.rate_per_day * 2
            elif n == 50:
                api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
                bill = Bill.objects.get(booking=booking)
                original = bill.total_amount
                old.rate_per_day = Decimal("9999.00")
                old.save()
                bill.refresh_from_db()
                assert bill.total_amount == original
            else:
                old.effective_from = today - timedelta(days=2)
                old.save()
                newer, _ = Tariff.objects.get_or_create(category=category, room_type=room.room_type, occupancy_type=room.occupancy_type, effective_from=today, defaults={"rate_per_day": Decimal("900.00")})
                assert newer.effective_from >= old.effective_from
        return

    if 51 <= n <= 58:
        booking = make_booking(category, status=BookingStatus.CHECKED_IN, days=0, stay=2)
        if n == 51 or n == 52:
            meal_type, addon = "FULL_DAY", "NONE"
        elif n == 53:
            meal_type, addon = "BREAKFAST", "NONE"
        elif n == 54:
            meal_type, addon = "FULL_DAY", "TEA"
        elif n == 55:
            meal_type, addon = "BRUNCH", "NONE"
        elif n == 56:
            meal_type, addon = "FULL_DAY", "COFFEE"
        else:
            meal_type, addon = "LUNCH", "NONE"
        if n == 53:
            for mt in ("BREAKFAST", "LUNCH", "DINNER"):
                response = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date), "meal_type": mt, "add_on": "NONE", "number_of_persons": 1, "rate": "100.00"}, format="json")
                assert response.status_code == 201
        elif n == 54:
            for add_on in ("TEA", "MILK"):
                response = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date), "meal_type": "FULL_DAY", "add_on": add_on, "rate": "100.00"}, format="json")
                assert response.status_code == 201
        else:
            response = api_client.post("/api/v1/vh/meals/", {"booking": booking.id, "date": str(booking.check_in_date + timedelta(days=3) if n == 57 else booking.check_in_date), "meal_type": meal_type, "add_on": addon, "number_of_persons": 1, "rate": "100.00"}, format="json")
            if n in (55, 56, 57):
                assert response.status_code == 400
                assert MealBooking.objects.filter(booking=booking).count() == 0
            else:
                assert response.status_code == 201
                if n == 58:
                    api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
                    assert Bill.objects.get(booking=booking).meal_charges == Decimal("100.00")
        return

    if 59 <= n <= 66:
        booking = make_booking(category, status=BookingStatus.APPROVED if n == 61 else BookingStatus.CHECKED_IN, days=3 if n == 61 else 0, stay=2)
        room = all_room_combinations[0]
        RoomAllotment.objects.create(booking=booking, room=room, check_in_time=timezone.now())
        if n in (60, 58):
            MealBooking.objects.create(booking=booking, date=booking.check_in_date, meal_type="LUNCH", number_of_persons=1, rate=Decimal("100.00"), total_amount=Decimal("100.00"))
        if n in (61,):
            booking.calculated_cancellation_charge = Decimal("100.00")
        if n in (59, 60, 65):
            response = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {"guest_verification_notes": "Verified"}, format="json")
            assert response.status_code == 200
            bill = Bill.objects.get(booking=booking)
            if n == 59:
                assert bill.room_charges > 0
            elif n == 60:
                assert bill.meal_charges == Decimal("100.00")
            elif n == 65:
                assert bill.guest_verification_notes == "Verified"
        elif n == 61:
            booking.status = BookingStatus.APPROVED
            booking.save()
            cancellation = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
            assert cancellation.status_code == 200
            confirmed = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/", {}, format="json")
            assert confirmed.status_code == 200
            assert Decimal(confirmed.data["bill"]["cancellation_charges"]) == Decimal(cancellation.data["applicable_cancellation_charge"])
        elif n == 62:
            created = post_booking(api_client, category.id, billing_responsibility="PROJECT")
            assert created.status_code == 201 and created.data["billing_responsibility"] == "PROJECT"
        elif n in (63, 64):
            bill = Bill.objects.create(booking=booking, room_charges=Decimal("100.00"), total_amount=Decimal("100.00"))
            response = api_client.post(f"/api/v1/vh/bills/{bill.id}/settle/", {"payment_mode": "CASH", "guest_verification_notes": "Cash received"}, format="json")
            assert response.status_code == 200
            assert response.data["payment_mode"] == "CASH" and response.data["is_settled"] is True
            assert response.data["guest_verification_notes"] == "Cash received"
        elif n == 66:
            bill = Bill.objects.create(booking=booking, room_charges=Decimal("100.00"), total_amount=Decimal("100.00"), is_finalized=True)
            response = api_client.put(f"/api/v1/vh/bills/{bill.id}/", {"booking": booking.id, "room_charges": "500.00", "meal_charges": "0.00", "cancellation_charges": "0.00", "total_amount": "500.00", "payment_mode": "CASH", "is_finalized": True}, format="json")
            assert response.status_code == 400
            bill.refresh_from_db()
            assert bill.total_amount == Decimal("100.00")
        return

    if 68 <= n <= 72:
        quantity, threshold = (2, 5) if n == 72 else (12, 5)
        response = api_client.post("/api/v1/vh/inventory/", {"name": f"FR-item-{n}", "category": "LINEN", "current_quantity": quantity, "minimum_threshold": threshold}, format="json")
        assert response.status_code == 201
        assert response.data["current_quantity"] == quantity
        if n == 72:
            assert response.data["is_below_threshold"] is True
            assert VHAlert.objects.filter(inventory_item_id=response.data["id"], alert_type="INVENTORY_THRESHOLD").exists()
        return

    if n in (73, 74):
        item, _ = InventoryItem.objects.get_or_create(name=f"FR-replenish-{n}", defaults={"category": "LINEN", "current_quantity": 2, "minimum_threshold": 5})
        if n == 73:
            response = api_client.post(f"/api/v1/vh/inventory/{item.id}/request_replenishment/", {"quantity_requested": 4}, format="json")
            assert response.status_code == 201
        else:
            pending, _ = InventoryReplenishment.objects.get_or_create(item=item, quantity_requested=4, requested_by_user_id=1)
            response = api_client.post(f"/api/v1/vh/replenishments/{pending.id}/approve/", {}, format="json")
            assert response.status_code == 200
            assert response.data["status"] == "APPROVED"
        return

    if 76 <= n <= 80:
        if n in (76, 77, 78):
            booking = make_booking(category)
            if n == 76:
                api_client.post("/api/v1/vh/bookings/", {"indenter_id": 1, "visitor_name": "Notify", "visitor_email": "notify@example.test", "visitor_category": category.id, "visit_purpose": "Test", "check_in_date": str(today + timedelta(days=10)), "check_out_date": str(today + timedelta(days=12)), "billing_responsibility": "VISITOR"}, format="json")
                assert VHNotificationLog.objects.filter(event_type="BOOKING_SUBMITTED").exists()
            elif n == 77:
                api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/", {}, format="json")
                api_client.post(f"/api/v1/vh/bookings/{booking.id}/approve/", {}, format="json")
                assert VHNotificationLog.objects.filter(booking=booking, event_type="BOOKING_APPROVED").exists()
            elif n == 78:
                api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
                assert VHNotificationLog.objects.filter(booking=booking, event_type="CANCELLATION_REQUESTED").exists()
        elif n == 79:
            pytest.skip("NOT_AUTOMATED: the specification does not define a check-in/check-out reminder schedule or a triggering time condition")
        else:
            response = api_client.post("/api/v1/vh/inventory/", {"name": "FR-notification-threshold", "category": "LINEN", "current_quantity": 1, "minimum_threshold": 4}, format="json")
            assert response.status_code == 201
            item = InventoryItem.objects.get(pk=response.data["id"])
            assert VHNotificationLog.objects.filter(event_type="INVENTORY_THRESHOLD").exists()
            assert VHAlert.objects.filter(inventory_item=item, alert_type="INVENTORY_THRESHOLD").exists()
        return

    if 82 <= n <= 89:
        response = api_client.get("/api/v1/vh/reports/incharge/" if n <= 85 else "/api/v1/vh/reports/caretaker/")
        assert response.status_code == 200
        keys = {82: "booking_summary", 83: "category_occupancy", 84: "revenue_summary", 85: "inventory_usage", 86: "daily_occupancy", 87: "upcoming_arrivals", 88: "pending_actions", 89: "no_show_logs"}
        assert keys[n] in response.data
        return

    if 90 <= n <= 95:
        role_type = VHMSUserRoleType.CARETAKER if n in (90, 92, 93, 94, 95) else VHMSUserRoleType.IN_CHARGE
        role = VHMSUserRole.reassign_role(role_type, 5000 + n, start_date=today, end_date=today + timedelta(days=30))
        assert role.is_active is True
        if n in (90, 91):
            VHMSUserRole.reassign_role(role_type, 7000 + n, start_date=today)
            assert VHMSUserRole.objects.filter(role_type=role_type, is_active=True).count() == 1
        elif n == 92:
            assert role.start_date == today and role.end_date == today + timedelta(days=30)
        elif n == 93:
            assert VHMSUserRole.get_active_caretaker().user_id == role.user_id
        else:
            status_filter = [BookingStatus.PENDING, BookingStatus.ROOM_ALLOTTED, BookingStatus.CHECKED_IN] if n == 94 else [BookingStatus.ROOM_ALLOTTED, BookingStatus.CHECKED_IN]
            booking = make_booking(category, status=status_filter[0])
            VHMSUserRole.reassign_role(role_type, 6000 + n, start_date=today)
            booking.refresh_from_db()
            assert booking.assigned_caretaker_id == 6000 + n if role_type == VHMSUserRoleType.CARETAKER else booking.assigned_incharge_id == 6000 + n
        return

    raise AssertionError(f"No backend test implementation for {afr}")
